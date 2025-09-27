from pydantic import BaseModel


class OptimizerRequest(BaseModel):
    region: str = "us-east-1"

class EC2Request(OptimizerRequest):
    cpu_threshold: float = 5.0  # Default CPU threshold percentage