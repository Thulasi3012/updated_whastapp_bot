from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class WebhookRequest(BaseModel):
    entry:List[Dict[str, Any]]
