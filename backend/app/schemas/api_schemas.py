"""
Pydantic Request & Response Schemas (app/schemas/api_schemas.py)
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = Field(default="executive", description="admin, manager, or executive")
    phone: Optional[str] = None
    department: Optional[str] = "Healthcare & Real Estate Advisory"


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class MetaConnectRequest(BaseModel):
    app_id: str
    app_name: Optional[str] = "Space Consultant Meta Lead App"
    business_id: Optional[str] = None
    access_token: Optional[str] = None
    verify_token: Optional[str] = None
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    ad_account_id: Optional[str] = None
    ad_account_name: Optional[str] = None


class DoubleTickTestMessageRequest(BaseModel):
    recipient_phone: str
    message_type: str = Field(default="TEMPLATE", description="TEMPLATE, TEXT, IMAGE, or DOCUMENT")
    template_name: Optional[str] = "hospital_enquiry"
    language: str = "en"
    placeholders: List[str] = Field(default_factory=lambda: ["Dr. Guest", "100-Bed Multispeciality Hospital"])
    text: Optional[str] = None
    media_url: Optional[str] = None
    filename: Optional[str] = None
    caption: Optional[str] = None


class CampaignCreateRequest(BaseModel):
    name: str
    meta_campaign_id: str
    facebook_page_id: str
    ad_account_id: Optional[str] = "act_1029384756"
    lead_form_id: Optional[str] = None
    purpose: str = Field(
        ...,
        description="hospital_for_sale, doctor_recruitment, healthcare_recruitment, hospital_property, real_estate",
    )
    whatsapp_template_name: str
    template_language: str = "en"
    template_variables: Dict[str, Any] = Field(default_factory=dict)
    auto_reply_enabled: bool = True
    pdf_brochure_url: Optional[str] = None
    pdf_filename: Optional[str] = None
    image_attachment_url: Optional[str] = None
    website_url: Optional[str] = None
    followup_config: Dict[str, Any] = Field(default_factory=dict)
    assignment_config: Dict[str, Any] = Field(default_factory=dict)
    campaign_knowledge: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ACTIVE"
    description: Optional[str] = None


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    meta_campaign_id: Optional[str] = None
    facebook_page_id: Optional[str] = None
    lead_form_id: Optional[str] = None
    purpose: Optional[str] = None
    whatsapp_template_name: Optional[str] = None
    template_language: Optional[str] = None
    template_variables: Optional[Dict[str, Any]] = None
    auto_reply_enabled: Optional[bool] = None
    pdf_brochure_url: Optional[str] = None
    pdf_filename: Optional[str] = None
    image_attachment_url: Optional[str] = None
    website_url: Optional[str] = None
    followup_config: Optional[Dict[str, Any]] = None
    assignment_config: Optional[Dict[str, Any]] = None
    campaign_knowledge: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    description: Optional[str] = None


class LeadUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    lead_status: Optional[str] = None
    notes: Optional[str] = None
    whatsapp_opt_in: Optional[bool] = None
    opted_out: Optional[bool] = None
    automation_paused: Optional[bool] = None
    campaign_id: Optional[str] = None


class LeadAssignRequest(BaseModel):
    executive_id: Optional[str] = None
    executive_name: str
    notes: Optional[str] = None


class LeadResendRequest(BaseModel):
    template_name: Optional[str] = None
    force_template: bool = True


class TemplateCreateRequest(BaseModel):
    template_name: str
    language: str = "en"
    category: str = "UTILITY"
    purpose: str
    header_type: str = "NONE"
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = "Space Consultant • Reply STOP to opt out"
    variables_schema: List[str] = Field(default_factory=list)
    buttons_schema: List[Dict[str, Any]] = Field(default_factory=list)
    approval_status: str = "APPROVED"
    is_active: bool = True


class TemplateUpdateRequest(BaseModel):
    language: Optional[str] = None
    category: Optional[str] = None
    purpose: Optional[str] = None
    header_type: Optional[str] = None
    header_text: Optional[str] = None
    body_text: Optional[str] = None
    footer_text: Optional[str] = None
    variables_schema: Optional[List[str]] = None
    buttons_schema: Optional[List[Dict[str, Any]]] = None
    approval_status: Optional[str] = None
    is_active: Optional[bool] = None


class FollowupCreateRequest(BaseModel):
    lead_id: str
    step_number: int = 2
    delay_hours: int = 24
    template_name: str
    template_language: str = "en"
    template_variables: Dict[str, Any] = Field(default_factory=dict)


class FollowupUpdateRequest(BaseModel):
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    template_name: Optional[str] = None
    cancellation_reason: Optional[str] = None


class SystemSettingUpdateRequest(BaseModel):
    settings: Dict[str, Any]
