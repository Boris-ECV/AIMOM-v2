"""AWS Lambda 進入點（TASK-012）。

透過 Mangum 將既有 FastAPI app 包裝成 Lambda handler，
供 API Gateway (HTTP API) 呼叫，不需重寫框架程式碼。
"""
from mangum import Mangum

from app import app

handler = Mangum(app)
