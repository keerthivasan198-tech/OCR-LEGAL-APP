# -*- coding: utf-8 -*-
"""Runner script for Property Document OCR Web Server"""
import uvicorn

if __name__ == "__main__":
    print("=========================================================")
    print("  Starting Real Estate Document OCR & Intelligence Server")
    print("  Access Web Application at: http://127.0.0.1:8000")
    print("=========================================================")
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, reload=False, access_log=True)
