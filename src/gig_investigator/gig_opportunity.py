# Data model for a gig opportunity
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class GigOpportunity:
	name: str
	date: Optional[str] = None
	location: Optional[str] = None
	contact_email: Optional[str] = None
	url: Optional[str] = None
