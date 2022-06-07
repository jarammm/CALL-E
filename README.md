# CALL-E
-- 프로젝트 설명란 --
채팅 로그 요약문으로 단체카톡방 대표 이미지를 생성해주는 ChatDALL-E

## 1. About Us

### Members

임동진|정재윤|조설아|허치영|이보림|
:-:|:-:|:-:|:-:|:-:
<img src='https://avatars.githubusercontent.com/u/72785706?v=4' height=80 width=80px></img>|<img src='https://avatars.githubusercontent.com/u/71070496?v=4' height=80 width=80px></img>|<img src='https://avatars.githubusercontent.com/u/90924434?v=4' height=80 width=80px></img>|<img src='https://avatars.githubusercontent.com/u/69616444?v=4' height=80 width=80px></img>|<img src='https://avatars.githubusercontent.com/u/55435898?v=4' height=80 width=80px></img>|
[Github](https://github.com/idj7183)|[Github](https://github.com/kma7574)|[Github](https://github.com/jarammm)|[Github](https://github.com/mooncy0421)|[Github](https://github.com/bo-lim)

### Contribution  

`임동진` &nbsp; : &nbsp; Dialogue Summarization • Backend <br>
`정재윤` &nbsp; : &nbsp; Dataset Processing • Frontend <br>
`조설아` &nbsp; : &nbsp; Text-to-Image • Text processing <br>
`허치영` &nbsp; : &nbsp; Dialogue Summarization • Documentation <br>
`이보림` &nbsp; : &nbsp; Text-to-Image • Image Dataset <br>
<br>

## 2. Project

### 프로젝트 목표
- 목표
  - [작성 예정]
- 기능
  - 최근 대화 내역의 요약 문장 제공
  - 최근 대화 내역 요약 문장을 나타내는 이미지 제공


### 프로젝트 구조
-- block diagram -- 

## 3. 시연 영상
-- 영상 -- 

## 4. Usage

```
.
├── summarization
│   ├── ...
│   ├── SBERT
│   │   ├── ...
│   │   ├── README.md
│   │   ├── __init__.py
│   │   └── sbert.py
│   ├── cache_data
│   │   ├── ...
│   │   └── Trash Data.txt
│   ├── data
│   │   ├── ...
│   │   └── README.md
│   ├── data_loader
│   │   ├── ...
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── get_data.py
│   │   ├── processing.py
│   │   └── tokenized_data.py
│   ├── logger
│   │   ├── ...
│   │   ├── __init__.py
│   │   └── logger.py
│   ├── tokenizer
│   │   ├── ...
│   │   ├── README.md
│   │   ├── __init__.py
│   │   └── tokenzier.py
│   ├── README.md
│   ├── __init__.py
│   ├── arguments.py
│   ├── configs.yaml
│   ├── inference.py
│   ├── inference_configs.yaml
│   ├── requirements.txt
│   ├── train.py
│   └── utils.py
├── text2image
│   ├── ...
│   ├── assets
│   ├── crawling
│   │   ├── ...
│   │   └── pixabay.py
│   ├── metric
│   │   ├── ...
│   │   ├── CLIP.py
│   │   └── FID.py
│   ├── model
│   │   ├── ...
│   │   ├── configs
│   │   │   ├── ...
│   │   │   └── CALL-E.yaml
│   │   ├── dalle
│   │   │   ├── ...
│   │   │   ├── data_loader
│   │   │   │   ├── ...
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dataset.py
│   │   │   │   └── utils.py
│   │   │   ├── logger
│   │   │   │   ├── ...
│   │   │   │   ├── __init__.py
│   │   │   │   └── loger.py
│   │   │   ├── models
│   │   │   │   ├── ...
│   │   │   │   ├── stage1
│   │   │   │   ├── stage2
│   │   │   │   ├── __init__.py
│   │   │   │   └── tokenizer.py
│   │   │   ├── utils
│   │   │   │   ├── ...
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   ├── sampling.py
│   │   │   │   └── utils.py
│   │   │   ├── LICENSE
│   │   │   ├── LICENSE.apache-2.0
│   │   │   ├── __init__.py
│   │   │   ├── ...inference.py
│   │   │   ├── train.py
│   │   │   └── translate.py
│   │   ├── test
│   │   ├── .gitattributes
│   │   ├── .gitignore
│   │   └── .setup.cfg
│   └── README.md
├── .gitignore
├── Dockerfile
├── README.md
├── app.py
├── cloudbuild.yaml
├── main.py
└── requirements.txt
```

## 5. References
### Datasets
- [AI Hub 한국어 대화 요약 데이터셋](https://aihub.or.kr/aidata/30714)
- [Pixabay](https://pixabay.com/ko/)

### Papers
- [Ham, Jiyeon, et al. "Kornli and korsts: New benchmark datasets for korean natural language understanding." arXiv preprint arXiv:2004.03289 (2020).](https://arxiv.org/pdf/2004.03289.pdf)
- [Lewis, Mike, et al. "Bart: Denoising sequence-to-sequence pre-training for natural language generation, translation, and comprehension." arXiv preprint arXiv:1910.13461 (2019).](https://arxiv.org/pdf/1910.13461.pdf)
- [Liu, Zhengyuan, and Nancy F. Chen. "Controllable Neural Dialogue Summarization with Personal Named Entity Planning." arXiv preprint arXiv:2109.13070 (2021).](https://arxiv.org/pdf/2109.13070.pdf)
- [Lee, Dongyub, et al. "Reference and document aware semantic evaluation methods for Korean language summarization." arXiv preprint arXiv:2005.03510 (2020).](https://arxiv.org/pdf/2005.03510.pdf)
- [Ramesh, Aditya, et al. "Zero-shot text-to-image generation." International Conference on Machine Learning. PMLR, 2021.](https://arxiv.org/pdf/2102.12092.pdf)
- [Zhou, Yufan, et al. "LAFITE: Towards Language-Free Training for Text-to-Image Generation." arXiv preprint arXiv:2111.13792 (2021).](https://arxiv.org/pdf/2111.13792.pdf)
- [Rombach, Robin, et al. "High-Resolution Image Synthesis with Latent Diffusion Models." arXiv preprint arXiv:2112.10752 (2021).](https://arxiv.org/pdf/2112.10752.pdf)

### Models
- [kakaobrain/minDALL-E](https://github.com/kakaobrain/minDALL-E)
- [STK-AI/KoBART](https://github.com/SKT-AI/KoBART)
- [AIRC-KETI/KE-T5](https://github.com/AIRC-KETI/ke-t5)
