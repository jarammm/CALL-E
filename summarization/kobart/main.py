#!/usr/bin/env python
# coding=utf-8
# Copyright 2021 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Fine-tuning the library models for sequence to sequence.
"""
# You can also adapt this script on your own sequence to sequence task. Pointers for this are left as comments.

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import datasets
import nltk  # Here to have a nice missing dependency error message early on
import numpy as np
from datasets import load_dataset, load_metric

import transformers
from filelock import FileLock
from transformers import (
    AutoConfig,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    TrainingArguments,
    set_seed,
    PreTrainedTokenizerFast,
    BartForConditionalGeneration
)
from transformers.trainer_utils import get_last_checkpoint
from transformers.utils import check_min_version#, is_offline_mode
from transformers.utils.versions import require_version

from arguments import *
from kobart_utils import *
import yaml

# Will error if the minimal version of Transformers is not installed. Remove at your own risks.
#check_min_version("4.20.0.dev0")

require_version("datasets>=1.8.0", "To fix: pip install -r examples/pytorch/summarization/requirements.txt")

logger = logging.getLogger(__name__)

try:
    nltk.data.find("tokenizers/punkt")
except (LookupError, OSError):
    # if is_offline_mode():
    #     raise LookupError(
    #         "Offline mode: run this script without TRANSFORMERS_OFFLINE first to download nltk data files"
    #     )
    with FileLock(".lock") as lock:
        nltk.download("punkt", quiet=True)
    
summarization_name_mapping = {
    "amazon_reviews_multi": ("review_body", "review_title"),
    "big_patent": ("description", "abstract"),
    "cnn_dailymail": ("article", "highlights"),
    "orange_sum": ("text", "summary"),
    "pn_summary": ("article", "summary"),
    "psc": ("extract_text", "summary_text"),
    "samsum": ("dialogue", "summary"),
    "thaisum": ("body", "summary"),
    "xglue": ("news_body", "news_title"),
    "xsum": ("document", "summary"),
    "wiki_summary": ("article", "highlights"),

    "aihub": ("dialogue", "summary")
}


def main():
    # See all possible arguments in src/transformers/training_args.py
    # or by passing the --help flag to this script.
    # We now keep distinct sets of args, for a cleaner separation of concerns.

    with open('./configs.yaml') as f:
        configs = yaml.load(f, Loader=yaml.FullLoader)
    training_args, model_args, data_args = configs['TrainingArguments'], configs['ModelArguments'], configs['DataTrainingArguments']
    model_args = ModelArguments(**model_args)
    data_args = DataTrainingArguments(**data_args)
    training_args = TrainingArguments(**training_args)
    training_args.predict_with_generate = True

    # Setup logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    log_level = logging.ERROR
    logger.setLevel(log_level)
    datasets.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.enable_default_handler()
    transformers.utils.logging.enable_explicit_format()

    # Log on each process the small summary:
    logger.warning(
        f"Process rank: {training_args.local_rank}, device: {training_args.device}, n_gpu: {training_args.n_gpu}"
        + f"distributed training: {bool(training_args.local_rank != -1)}, 16-bits training: {training_args.fp16}"
    )
    logger.info(f"Training/evaluation parameters {training_args}")

    # t5 model 전용 prefix 설정
    if data_args.source_prefix is None and model_args.model_name_or_path in [
        "t5-small",
        "t5-base",
        "t5-large",
        "t5-3b",
        "t5-11b",
    ]:
        logger.warning(
            "You're running a t5 model but didn't provide a source prefix, which is the expected, e.g. with "
            "`--source_prefix 'summarize: ' `"
        )

    # output directory 관련. overwrite 가능 여부 설정 및 이미 생성된 상태인지 확인
    # Detecting last checkpoint.
    last_checkpoint = None
    if os.path.isdir(training_args.output_dir) and training_args.do_train and not training_args.overwrite_output_dir:
        last_checkpoint = get_last_checkpoint(training_args.output_dir)
        if last_checkpoint is None and len(os.listdir(training_args.output_dir)) > 0:
            raise ValueError(
                f"Output directory ({training_args.output_dir}) already exists and is not empty. "
                "Use --overwrite_output_dir to overcome."
            )
        elif last_checkpoint is not None:
            logger.info(
                f"Checkpoint detected, resuming training at {last_checkpoint}. To avoid this behavior, change "
                "the `--output_dir` or add `--overwrite_output_dir` to train from scratch."
            )

    # Set seed before initializing model.
    set_seed(training_args.seed)

    # TODO: dataset load 부분 우리 데이터셋에 맞게 고치기
    # Get the datasets: you can either provide your own CSV/JSON training and evaluation files (see below)
    # or just provide the name of one of the public datasets available on the hub at https://huggingface.co/datasets/
    # (the dataset will be downloaded automatically from the datasets Hub).
    #
    # For CSV/JSON files this script will use the first column for the full texts and the second column for the
    # summaries (unless you specify column names for this with the `text_column` and `summary_column` arguments).
    #
    # In distributed training, the load_dataset function guarantee that only one local process can concurrently
    # download the dataset.

    # ========================================================================================================
    # if data_args.dataset_name is not None:
    #     # Downloading and loading a dataset from the hub.
    #     raw_datasets = load_dataset(
    #         data_args.dataset_name,
    #         data_args.dataset_config_name,
    #         cache_dir=model_args.cache_dir,
    #         use_auth_token=True if model_args.use_auth_token else None,
    #     )
    # else:
    #     data_files = {}
    #     if data_args.train_file is not None:
    #         data_files["train"] = data_args.train_file
    #         extension = data_args.train_file.split(".")[-1]
    #     if data_args.validation_file is not None:
    #         data_files["validation"] = data_args.validation_file
    #         extension = data_args.validation_file.split(".")[-1]
    #     if data_args.test_file is not None:
    #         data_files["test"] = data_args.test_file
    #         extension = data_args.test_file.split(".")[-1]
    #     raw_datasets = load_dataset(
    #         extension,
    #         data_files=data_files,
    #         cache_dir=model_args.cache_dir,
    #         use_auth_token=True if model_args.use_auth_token else None,
    #     )
    # ========================================================================================================
    

    # For AIHub data
    data_files = {}
    data_files['train'] = data_args.train_file
    data_files['validation'] = data_args.validation_file
    data_files['test'] = data_args.test_file
    raw_datasets = load_dataset(
        data_args.data_file_type,
        data_files = data_files,
        cache_dir=model_args.cache_dir,
        field='data'
    )

    
    # See more about loading any type of standard or custom dataset (from files, python dict, pandas DataFrame, etc) at
    # https://huggingface.co/docs/datasets/loading_datasets.html.
    # ===========================================================================================================================


    # Pretrained model, tokenizer 로드 부분
    # TODO: Tokenizer 변경하는 방법 생각해보기 ex: monologg
    # Load pretrained model and tokenizer
    #
    # Distributed training:
    # The .from_pretrained methods guarantee that only one local process can concurrently
    # download model & vocab.



    # config = AutoConfig.from_pretrained(
    #     model_args.config_name if model_args.config_name else model_args.model_name_or_path,
    #     cache_dir=model_args.cache_dir,
    #     revision=model_args.model_revision,
    #     use_auth_token=True if model_args.use_auth_token else None,
    # )
    # tokenizer = AutoTokenizer.from_pretrained(
    #     model_args.tokenizer_name if model_args.tokenizer_name else model_args.model_name_or_path,
    #     cache_dir=model_args.cache_dir,
    #     use_fast=model_args.use_fast_tokenizer,
    #     revision=model_args.model_revision,
    #     use_auth_token=True if model_args.use_auth_token else None,
    # )
    # model = AutoModelForSeq2SeqLM.from_pretrained(
    #     model_args.model_name_or_path,
    #     from_tf=bool(".ckpt" in model_args.model_name_or_path),
    #     config=config,
    #     cache_dir=model_args.cache_dir,
    #     revision=model_args.model_revision,
    #     use_auth_token=True if model_args.use_auth_token else None,
    # )
    #tokenizer = PreTrainedTokenizerFast.from_pretrained(model_args.model_name_or_path)
    tokenizer = PTTFwithSaveVocab.from_pretrained(model_args.model_name_or_path)
    model = BartForConditionalGeneration.from_pretrained(model_args.model_name_or_path)

    model.resize_token_embeddings(len(tokenizer))

    # TODO: 다언어 Tokenizer language pair 필요 여부 확인 후 제거
    # if model.config.decoder_start_token_id is None and isinstance(tokenizer, (MBartTokenizer, MBartTokenizerFast)):
    #     if isinstance(tokenizer, MBartTokenizer):
    #         model.config.decoder_start_token_id = tokenizer.lang_code_to_id[data_args.lang]
    #     else:
    #         model.config.decoder_start_token_id = tokenizer.convert_tokens_to_ids(data_args.lang)

    # Decoder 시작 토큰 설정
    if model.config.decoder_start_token_id is None:
        raise ValueError("Make sure that `config.decoder_start_token_id` is correctly defined")

    # TODO: position embedding 크기 resize
    if (
        hasattr(model.config, "max_position_embeddings")
        and model.config.max_position_embeddings < data_args.max_source_length
    ):
        if model_args.resize_position_embeddings is None:
            logger.warning(
                "Increasing the model's number of position embedding vectors from"
                f" {model.config.max_position_embeddings} to {data_args.max_source_length}."
            )
            model.resize_position_embeddings(data_args.max_source_length)
        elif model_args.resize_position_embeddings:
            model.resize_position_embeddings(data_args.max_source_length)
        else:
            raise ValueError(
                f"`--max_source_length` is set to {data_args.max_source_length}, but the model only has"
                f" {model.config.max_position_embeddings} position encodings. Consider either reducing"
                f" `--max_source_length` to {model.config.max_position_embeddings} or to automatically resize the"
                " model's position encodings by passing `--resize_position_embeddings`."
            )

    prefix = data_args.source_prefix if data_args.source_prefix is not None else ""

    # Preprocessing the datasets.
    # We need to tokenize inputs and targets.
    if training_args.do_train:
        column_names = raw_datasets["train"].column_names
    elif training_args.do_eval:
        column_names = raw_datasets["validation"].column_names
    elif training_args.do_predict:
        column_names = raw_datasets["test"].column_names
    else:
        logger.info("There is nothing to do. Please pass `do_train`, `do_eval` and/or `do_predict`.")
        return

    # TODO: 다언어 tokenizer 언어 쌍 설정 과정
    # if isinstance(tokenizer, tuple(MULTILINGUAL_TOKENIZERS)):
    #     assert (
    #         data_args.lang is not None
    #     ), f"{tokenizer.__class__.__name__} is a multilingual tokenizer which requires --lang argument"

    #     tokenizer.src_lang = data_args.lang
    #     tokenizer.tgt_lang = data_args.lang

    #     # For multilingual translation models like mBART-50 and M2M100 we need to force the target language token
    #     # as the first generated token. We ask the user to explicitly provide this as --forced_bos_token argument.
    #     forced_bos_token_id = (
    #         tokenizer.lang_code_to_id[data_args.forced_bos_token] if data_args.forced_bos_token is not None else None
    #     )
    #     model.config.forced_bos_token_id = forced_bos_token_id
        # ===========================================================================================================================

    # Dataset의 column 매핑 받아 오는 과정
    # text, summary 순으로 받아옴
    # Get the column names for input/target.
    dataset_columns = summarization_name_mapping.get(data_args.dataset_name, None)
    if data_args.text_column is None:
        text_column = dataset_columns[0] if dataset_columns is not None else column_names[0]
    else:
        text_column = data_args.text_column
        if text_column not in column_names:
            raise ValueError(
                f"--text_column' value '{data_args.text_column}' needs to be one of: {', '.join(column_names)}"
            )
    if data_args.summary_column is None:
        summary_column = dataset_columns[1] if dataset_columns is not None else column_names[1]
    else:
        summary_column = data_args.summary_column
        if summary_column not in column_names:
            raise ValueError(
                f"--summary_column' value '{data_args.summary_column}' needs to be one of: {', '.join(column_names)}"
            )
    # ===========================================================================================================================


    # target값 최대 길이 설정 및 padding 설정
    # Temporarily set max_target_length for training.
    max_target_length = data_args.max_target_length
    padding = "max_length" if data_args.pad_to_max_length else False

    # TODO: prepare_decoder_input_ids_from_labels 함수 뭔지 확인
    if training_args.label_smoothing_factor > 0 and not hasattr(model, "prepare_decoder_input_ids_from_labels"):
        logger.warning(
            "label_smoothing is enabled but the `prepare_decoder_input_ids_from_labels` method is not defined for"
            f"`{model.__class__.__name__}`. This will lead to loss being calculated twice and will take up more memory"
        )

    # 데이터 preprocess 과정
    def preprocess_function(examples):
        # remove pairs where at least one record is None

        inputs, targets = [], []
        for i in range(len(examples[text_column])):
            # example의 text와 summary가 쌍으로 존재하는 경우에만 사용
            if examples[text_column][i] is not None and examples[summary_column][i] is not None:
                inputs.append(examples[text_column][i])
                targets.append(examples[summary_column][i])

        # input에 prefix 추가 (t5 계열 모델만 prefix 사용함)
        inputs = [prefix + inp for inp in inputs]
        # prefix 추가한 input text를 tokenizer 통해 id로 변경 == model_inputs
        model_inputs = tokenizer(inputs, max_length=data_args.max_source_length, padding=padding, truncation=True)

        # target summary를 tokenizer 통해 id로 변경 == labels
        # Setup the tokenizer for targets
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=max_target_length, padding=padding, truncation=True)

        # If we are padding here, replace all tokenizer.pad_token_id in the labels by -100 when we want to ignore
        # padding in the loss.
        # labels에서 padding 있으면 loss 계산 위해 pad_token_id를 -100으로 설정해서 무시하도록 함
        if padding == "max_length" and data_args.ignore_pad_token_for_loss:
            labels["input_ids"] = [
                [(l if l != tokenizer.pad_token_id else -100) for l in label] for label in labels["input_ids"]
            ]

        # model에 입력으로 들어가면 inputs (text)에 labels 달아서 전달함
        # 이 때 이미 preprocess_function 시작부분에서 input-target쌍 맞는 것만 사용하기 때문에 쌍은 항상 일치
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    # train 과정
    if training_args.do_train:
        if "train" not in raw_datasets:
            raise ValueError("--do_train requires a train dataset")
        train_dataset = raw_datasets["train"]
        if data_args.max_train_samples is not None:
            max_train_samples = min(len(train_dataset), data_args.max_train_samples)
            train_dataset = train_dataset.select(range(max_train_samples))
        # TODO: main_process_first 알아보기
        # with training_args.main_process_first(desc="train dataset map pre-processing"):
        #     # train dataset 준비 (validation, test 전부 다 방식은 같음)
        #     train_dataset = train_dataset.map(
        #         preprocess_function,
        #         batched=True,
        #         num_proc=data_args.preprocessing_num_workers,
        #         remove_columns=column_names,
        #         load_from_cache_file=not data_args.overwrite_cache,
        #         desc="Running tokenizer on train dataset",
        #     )
        train_dataset = train_dataset.map(
            preprocess_function,
            batched=True,
            num_proc=data_args.preprocessing_num_workers,
            remove_columns=column_names,
            load_from_cache_file=not data_args.overwrite_cache,
            desc="Running tokenizer on train dataset",
        )

    if training_args.do_eval:
        max_target_length = data_args.val_max_target_length
        if "validation" not in raw_datasets:
            raise ValueError("--do_eval requires a validation dataset")
        eval_dataset = raw_datasets["validation"]
        if data_args.max_eval_samples is not None:
            max_eval_samples = min(len(eval_dataset), data_args.max_eval_samples)
            eval_dataset = eval_dataset.select(range(max_eval_samples))
        # with training_args.main_process_first(desc="validation dataset map pre-processing"):
        #     eval_dataset = eval_dataset.map(
        #         preprocess_function,
        #         batched=True,
        #         num_proc=data_args.preprocessing_num_workers,
        #         remove_columns=column_names,
        #         load_from_cache_file=not data_args.overwrite_cache,
        #         desc="Running tokenizer on validation dataset",
        #     )
        eval_dataset = eval_dataset.map(
            preprocess_function,
            batched=True,
            num_proc=data_args.preprocessing_num_workers,
            remove_columns=column_names,
            load_from_cache_file=not data_args.overwrite_cache,
            desc="Running tokenizer on validation dataset",
        )

    if training_args.do_predict:
        max_target_length = data_args.val_max_target_length
        if "test" not in raw_datasets:
            raise ValueError("--do_predict requires a test dataset")
        predict_dataset = raw_datasets["test"]
        if data_args.max_predict_samples is not None:
            max_predict_samples = min(len(predict_dataset), data_args.max_predict_samples)
            predict_dataset = predict_dataset.select(range(max_predict_samples))
        # with training_args.main_process_first(desc="prediction dataset map pre-processing"):
        #     predict_dataset = predict_dataset.map(
        #         preprocess_function,
        #         batched=True,
        #         num_proc=data_args.preprocessing_num_workers,
        #         remove_columns=column_names,
        #         load_from_cache_file=not data_args.overwrite_cache,
        #         desc="Running tokenizer on prediction dataset",
        #     )
        predict_dataset = predict_dataset.map(
            preprocess_function,
            batched=True,
            num_proc=data_args.preprocessing_num_workers,
            remove_columns=column_names,
            load_from_cache_file=not data_args.overwrite_cache,
            desc="Running tokenizer on prediction dataset",
        )

    # Data collator
    label_pad_token_id = -100 if data_args.ignore_pad_token_for_loss else tokenizer.pad_token_id
    data_collator = DataCollatorForSeq2Seq(
        tokenizer,
        model=model,
        label_pad_token_id=label_pad_token_id,
        pad_to_multiple_of=8 if training_args.fp16 else None,
    )

    # Metric (ROUGE)
    metric = load_metric("rouge")

    def postprocess_text(preds, labels):
        preds = [pred.strip() for pred in preds]
        labels = [label.strip() for label in labels]

        # rougeLSum expects newline after each sentence
        # prediction, labels 각 문장 끝에 줄바꿈 붙이기
        preds = ["\n".join(nltk.sent_tokenize(pred)) for pred in preds]
        labels = ["\n".join(nltk.sent_tokenize(label)) for label in labels]

        return preds, labels

    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        if isinstance(preds, tuple):
            preds = preds[0]
        # prediction tokenizer로 decoding해서 문장으로 바꿈
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        # labels에서 -100으로 된 padding 제외
        if data_args.ignore_pad_token_for_loss:
            # Replace -100 in the labels as we can't decode them.
            labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

        # Some simple post-processing
        decoded_preds, decoded_labels = postprocess_text(decoded_preds, decoded_labels)

        result = metric.compute(predictions=decoded_preds, references=decoded_labels, use_stemmer=True)
        # Extract a few results from ROUGE
        result = {key: value.mid.fmeasure * 100 for key, value in result.items()}

        prediction_lens = [np.count_nonzero(pred != tokenizer.pad_token_id) for pred in preds]
        result["gen_len"] = np.mean(prediction_lens)
        result = {k: round(v, 4) for k, v in result.items()}
        return result

    # Initialize our Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset if training_args.do_train else None,
        eval_dataset=eval_dataset if training_args.do_eval else None,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics if training_args.predict_with_generate else None,
    )
    # trainer = S2STrainerwithRougeMetric(
    #     model=model,
    #     args=training_args,
    #     train_dataset=train_dataset if training_args.do_train else None,
    #     eval_dataset=eval_dataset if training_args.do_eval else None,
    #     tokenizer=tokenizer,
    #     data_collator=data_collator,
    #     compute_metrics=compute_metrics if training_args.predict_with_generate else None,
    # )

    # Training
    if training_args.do_train:
        checkpoint = None
        if last_checkpoint is not None:
            checkpoint = last_checkpoint
        elif os.path.isdir(model_args.model_name_or_path):
            checkpoint = model_args.model_name_or_path
        train_result = trainer.train(resume_from_checkpoint=checkpoint)
        trainer.save_model()  # Saves the tokenizer too for easy upload

        metrics = train_result.metrics
        max_train_samples = (
            data_args.max_train_samples if data_args.max_train_samples is not None else len(train_dataset)
        )
        metrics["train_samples"] = min(max_train_samples, len(train_dataset))

        trainer.log_metrics("train", metrics)
        trainer.save_metrics("train", metrics)
        #trainer.save_state()
        trainer.state.save_to_json(
            os.path.join(training_args.output_dir, "trainer_state.json")
        )

    # Evaluation
    results = {}
    # max_length = (
    #     training_args.generation_max_length
    #     if training_args.generation_max_length is not None
    #     else data_args.val_max_target_length
    # )
    max_length = data_args.val_max_target_length
    num_beams = data_args.num_beams
    if training_args.do_eval:
        logger.info("*** Evaluate ***")
        metrics = trainer.evaluate(max_length=max_length, num_beams=num_beams, metric_key_prefix="eval")
        max_eval_samples = data_args.max_eval_samples if data_args.max_eval_samples is not None else len(eval_dataset)
        metrics["eval_samples"] = min(max_eval_samples, len(eval_dataset))

        trainer.log_metrics("eval", metrics)
        trainer.save_metrics("eval", metrics)

    if training_args.do_predict:
        logger.info("*** Predict ***")

        # Predict 시작
        predict_results = trainer.predict(
            predict_dataset, metric_key_prefix="predict", max_length=max_length, num_beams=num_beams
        )
        metrics = predict_results.metrics
        max_predict_samples = (
            data_args.max_predict_samples if data_args.max_predict_samples is not None else len(predict_dataset)
        )
        metrics["predict_samples"] = min(max_predict_samples, len(predict_dataset))

        trainer.log_metrics("predict", metrics)
        trainer.save_metrics("predict", metrics)

        # TODO: Trainer.is_world_process_zero() 뭔지 알아야할 듯
        if trainer.is_world_process_zero():
            # Generative metric 후 결과 문장 생성
            if training_args.predict_with_generate:
                predictions = tokenizer.batch_decode(
                    predict_results.predictions, skip_special_tokens=True, clean_up_tokenization_spaces=True
                )
                predictions = [pred.strip() for pred in predictions]
                # output_dir에 generated_predictions.txt로 결과 저장
                output_prediction_file = os.path.join(training_args.output_dir, "generated_predictions.txt")
                with open(output_prediction_file, "w") as writer:
                    writer.write("\n".join(predictions))

    kwargs = {"finetuned_from": model_args.model_name_or_path, "tasks": "summarization"}
    if data_args.dataset_name is not None:
        kwargs["dataset_tags"] = data_args.dataset_name
        if data_args.dataset_config_name is not None:
            kwargs["dataset_args"] = data_args.dataset_config_name
            kwargs["dataset"] = f"{data_args.dataset_name} {data_args.dataset_config_name}"
        else:
            kwargs["dataset"] = data_args.dataset_name

    # if data_args.lang is not None:
    #     kwargs["language"] = data_args.lang

    # huggingface hub에 모델 업로드하는 부분 (default: False)
    # if training_args.push_to_hub:
    #     trainer.push_to_hub(**kwargs)
    # else:
    #     trainer.create_model_card(**kwargs)

    return results

if __name__ == "__main__":
    main()