import os
from PIL import Image
from lmdeploy import pipeline, TurbomindEngineConfig, GenerationConfig
from lmdeploy.vl import load_image

MODEL_PATH = os.environ.get("MODEL_PATH", "./weights/InternVL2-1B-finetuned-table-v5")

pipe = pipeline(
    model_path=MODEL_PATH,
    backend_config=TurbomindEngineConfig(session_len=12000)
)

gen_config = GenerationConfig(
    temperature=0.2,
    top_p=0.9,
    max_new_tokens=8192,
    do_sample=True
)

def image_to_latex(image: Image.Image) -> str:
    """
    接收一个 PIL.Image 图片，返回本地 lmdeploy 推理的 LaTeX 字符串。
    """
    image_input = load_image(image)
    response = pipe(
        ("Convert this table to LaTeX.", image_input),
        gen_config=gen_config
    )
    return response.text
