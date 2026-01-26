"""
OCR引擎封装
支持多种OCR引擎: PaddleOCR, Tesseract, 阿里云OCR
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod
import numpy as np

logger = logging.getLogger(__name__)


class OCREngineInterface(ABC):
    """OCR引擎接口"""

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    @abstractmethod
    def recognize(self, image: np.ndarray) -> Dict:
        """
        识别图片中的文字
        返回: {
            "text": "识别的文本",
            "boxes": [[x1,y1,x2,y2,text,confidence], ...],
            "confidence": 0.95
        }
        """
        pass

    @abstractmethod
    def recognize_table(self, image: np.ndarray) -> Dict:
        """
        识别表格
        返回: {
            "html": "<table>...</table>",
            "cells": [[...], ...],
            "confidence": 0.90
        }
        """
        pass


class PaddleOCREngine(OCREngineInterface):
    """PaddleOCR引擎实现"""

    def __init__(self):
        self._engine = None
        self._table_engine = None
        self._initialized = False

        try:
            from paddleocr import PaddleOCR
            # 初始化文字识别引擎
            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                use_gpu=False,  # 可配置
                show_log=False
            )
            # 初始化表格识别引擎
            try:
                from paddleocr import PPStructure
                self._table_engine = PPStructure(
                    use_gpu=False,
                    show_log=False,
                    layout=True,
                    table=True,
                    ocr=True
                )
            except ImportError:
                logger.warning("PPStructure not available, table recognition limited")

            self._initialized = True
            logger.info("PaddleOCR engine initialized successfully")
        except ImportError:
            logger.warning("PaddleOCR not installed")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")

    def is_available(self) -> bool:
        return self._initialized and self._engine is not None

    def recognize(self, image: np.ndarray) -> Dict:
        """识别图片中的文字"""
        if not self.is_available():
            raise RuntimeError("PaddleOCR engine not available")

        try:
            result = self._engine.ocr(image, cls=True)

            if not result or not result[0]:
                return {"text": "", "boxes": [], "confidence": 0.0}

            boxes = []
            texts = []
            confidences = []

            for line in result[0]:
                box = line[0]  # 坐标
                text_and_conf = line[1]  # (text, confidence)

                boxes.append([int(p[0]) for p in box] + [int(p[1]) for p in box])
                texts.append(text_and_conf[0])
                confidences.append(text_and_conf[1])

            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": "\n".join(texts),
                "boxes": [
                    {
                        "coordinates": [int(p) for p in line[0]],
                        "text": line[1][0],
                        "confidence": line[1][1]
                    }
                    for line in result[0]
                ],
                "confidence": avg_confidence
            }
        except Exception as e:
            logger.error(f"PaddleOCR recognition error: {e}")
            return {"text": "", "boxes": [], "confidence": 0.0}

    def recognize_table(self, image: np.ndarray) -> Dict:
        """识别表格"""
        if not self.is_available():
            raise RuntimeError("PaddleOCR engine not available")

        try:
            if self._table_engine:
                result = self._table_engine(image)

                # 解析表格结果
                tables = []
                for item in result:
                    if item.get('type') == 'table':
                        # 提取表格HTML和单元格
                        tables.append({
                            "html": item.get('res', {}).get('html', ''),
                            "cells": item.get('res', {}).get('cell_bbox', []),
                            "bbox": item.get('bbox', []),
                            "confidence": item.get('res', {}).get('score', 0.0)
                        })

                return {
                    "tables": tables,
                    "confidence": tables[0]["confidence"] if tables else 0.0
                }
            else:
                # 回退到普通OCR + 表格检测
                return {"tables": [], "confidence": 0.0}
        except Exception as e:
            logger.error(f"Table recognition error: {e}")
            return {"tables": [], "confidence": 0.0}


class AliCloudOCREngine(OCREngineInterface):
    """阿里云OCR引擎实现"""

    def __init__(self, access_key_id: str = None, access_key_secret: str = None):
        self._access_key_id = access_key_id or os.getenv("ALIYUN_ACCESS_KEY_ID")
        self._access_key_secret = access_key_secret or os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        self._endpoint = "https://ocr-api.cn-hangzhou.aliyuncs.com"
        self._initialized = False

        if self._access_key_id and self._access_key_secret:
            try:
                from alibabacloud_ocr_api20210707.client import Client
                from alibabacloud_tea_openapi import models as open_api_models
                from alibabacloud_ocr_api20210707 import models as ocr_models

                config = open_api_models.Config(
                    access_key_id=self._access_key_id,
                    access_key_secret=self._access_key_secret
                )
                config.endpoint = self._endpoint
                self._client = Client(config)
                self._initialized = True
                logger.info("AliCloud OCR engine initialized")
            except ImportError:
                logger.warning("AliCloud OCR SDK not installed")
            except Exception as e:
                logger.error(f"Failed to initialize AliCloud OCR: {e}")

    def is_available(self) -> bool:
        return self._initialized

    def recognize(self, image_bytes: bytes) -> Dict:
        """识别图片中的文字"""
        if not self.is_available():
            raise RuntimeError("AliCloud OCR engine not available")

        try:
            from alibabacloud_ocr_api20210707.models import RecognizeGeneralRequest

            request = RecognizeGeneralRequest()
            request.body = image_bytes

            response = self._client.recognize_general(request)

            return {
                "text": response.body.data.content,
                "boxes": [
                    {
                        "text": box.text,
                        "confidence": box.confidence,
                        "coordinates": [
                            box.left_top.x, box.left_top.y,
                            box.right_top.x, box.right_top.y,
                            box.right_bottom.x, box.right_bottom.y,
                            box.left_bottom.x, box.left_bottom.y
                        ]
                    }
                    for box in response.body.data.prism_words_info
                ],
                "confidence": response.body.data.confidence
            }
        except Exception as e:
            logger.error(f"AliCloud OCR error: {e}")
            return {"text": "", "boxes": [], "confidence": 0.0}

    def recognize_table(self, image_bytes: bytes) -> Dict:
        """识别表格"""
        if not self.is_available():
            raise RuntimeError("AliCloud OCR engine not available")

        try:
            from alibabacloud_ocr_api20210707.models import RecognizeTableRequest

            request = RecognizeTableRequest()
            request.body = image_bytes

            response = self._client.recognize_table(request)

            return {
                "tables": [{
                    "html": response.body.data.content,
                    "cells": [],
                    "confidence": response.body.data.confidence
                }],
                "confidence": response.body.data.confidence
            }
        except Exception as e:
            logger.error(f"AliCloud table recognition error: {e}")
            return {"tables": [], "confidence": 0.0}


class TesseractOCREngine(OCREngineInterface):
    """Tesseract OCR引擎实现"""

    def __init__(self):
        self._engine = None
        self._initialized = False

        try:
            import pytesseract
            from PIL import Image

            self._pytesseract = pytesseract
            self._PIL = Image
            self._initialized = True
            logger.info("Tesseract OCR engine initialized")
        except ImportError:
            logger.warning("pytesseract or PIL not installed")

    def is_available(self) -> bool:
        return self._initialized

    def recognize(self, image: np.ndarray) -> Dict:
        """识别图片中的文字"""
        if not self.is_available():
            raise RuntimeError("Tesseract engine not available")

        try:
            # 转换为PIL Image
            from PIL import Image
            pil_image = Image.fromarray(image)

            # 获取文本和详细数据
            data = self._pytesseract.image_to_data(
                pil_image,
                output_type=self._pytesseract.Output.DICT,
                lang='chi_sim+eng'
            )

            # 提取有效文本
            texts = []
            confidences = []

            for i, text in enumerate(data['text']):
                if text.strip():
                    conf = int(data['conf'][i])
                    if conf > 0:
                        texts.append(text)
                        confidences.append(conf / 100.0)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": "\n".join(texts),
                "boxes": [],
                "confidence": avg_confidence
            }
        except Exception as e:
            logger.error(f"Tesseract recognition error: {e}")
            return {"text": "", "boxes": [], "confidence": 0.0}

    def recognize_table(self, image: np.ndarray) -> Dict:
        """Tesseract不擅长表格识别，返回空结果"""
        return {"tables": [], "confidence": 0.0}


class OCREngine:
    """OCR引擎管理器"""

    def __init__(self, preferred_engine: str = "paddle"):
        """
        初始化OCR引擎
        preferred_engine: 首选引擎 (paddle/tesseract/aliyun)
        """
        self._engines: List[OCREngineInterface] = []
        self._preferred_engine = preferred_engine

        # 按优先级初始化引擎
        if preferred_engine == "paddle":
            self._engines.append(PaddleOCREngine())
        elif preferred_engine == "tesseract":
            self._engines.append(TesseractOCREngine())
        elif preferred_engine == "aliyun":
            self._engines.append(AliCloudOCREngine())

        # 添加备用引擎
        for engine_type in ["paddle", "tesseract", "aliyun"]:
            if engine_type != preferred_engine:
                if engine_type == "paddle":
                    self._engines.append(PaddleOCREngine())
                elif engine_type == "tesseract":
                    self._engines.append(TesseractOCREngine())
                elif engine_type == "aliyun":
                    self._engines.append(AliCloudOCREngine())

        # 找到第一个可用的引擎
        self._active_engine = None
        for engine in self._engines:
            if engine.is_available():
                self._active_engine = engine
                break

        if self._active_engine:
            logger.info(f"Using OCR engine: {type(self._active_engine).__name__}")
        else:
            logger.warning("No OCR engine available")

    def is_ready(self) -> bool:
        """检查是否有可用的OCR引擎"""
        return self._active_engine is not None

    def recognize(self, image: np.ndarray) -> Dict:
        """识别图片中的文字"""
        if not self.is_ready():
            raise RuntimeError("No OCR engine available")

        return self._active_engine.recognize(image)

    def recognize_table(self, image: np.ndarray) -> Dict:
        """识别表格"""
        if not self.is_ready():
            raise RuntimeError("No OCR engine available")

        return self._active_engine.recognize_table(image)

    def get_available_engines(self) -> List[str]:
        """获取可用的引擎列表"""
        return [
            type(e).__name__.replace("OCREngine", "").replace("Engine", "")
            for e in self._engines if e.is_available()
        ]
