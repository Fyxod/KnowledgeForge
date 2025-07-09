# from transformers import DonutProcessor, VisionEncoderDecoderModel
# from PIL import Image
# import torch
# print("running donut model")
# image = Image.open("image.png").convert("RGB")
# processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base")
# model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base")

# pixel_values = processor(image, return_tensors="pt").pixel_values
# outputs = model.generate(pixel_values)
# result = processor.batch_decode(outputs, skip_special_tokens=True)[0]
# print("Result from Donut model:")
# print(result)

# it's shit, maybe a small vision model or will use ocr as before