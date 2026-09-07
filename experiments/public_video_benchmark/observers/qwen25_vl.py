from __future__ import annotations

from .base import BaseObserver


class Qwen25VLObserver(BaseObserver):
    model_id = "Qwen/Qwen2.5-VL-3B-Instruct"

    def load(self) -> None:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_path, torch_dtype=dtype, device_map="auto", trust_remote_code=True
        ).eval()
        self.processor = AutoProcessor.from_pretrained(self.model_path, trust_remote_code=True)
