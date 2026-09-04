from paddleocr import TextRecognition

ocr = TextRecognition(
    model_name="ta_PP-OCRv5_mobile_rec"
)

result = ocr.predict("input/tamil.png")

for res in result:
    res.print()