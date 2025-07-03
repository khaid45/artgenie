from diffusers import StableDiffusionPipeline
import torch

def load_model():
    pipe = StableDiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-2-1-base",
        torch_dtype=torch.float32,
        safety_checker=None,
        low_cpu_mem_usage=True
    )
    return pipe.to("cpu")
