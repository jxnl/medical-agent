#!/usr/bin/env python3
"""
Telehealth Service with Session Management
Provides a durable agent service for handling telehealth interactions.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, TextBlock

logger = logging.getLogger(__name__)

# Controlled substances that require immediate escalation
CONTROLLED_SUBSTANCES = {
    "adderall", "xanax", "alprazolam", "oxycodone", "hydrocodone", "morphine",
    "fentanyl", "ritalin", "methylphenidate", "vyvanse", "lisdexamfetamine",
    "ativan", "lorazepam", "klonopin", "clonazepam", "valium", "diazepam",
    "ambien", "zolpidem", "tramadol", "codeine", "percocet", "vicodin"
}


@dataclass
class Session:
    session_id: str
    messages: list[dict]
    created_at: str
    updated_at: str


# Tool definitions (same as before)
@tool(
    "escalate_to_human",
    "Escalate the conversation to a healthcare provider or human agent when needed. Provide reason and urgency level.",
    {"reason": str, "urgency_level": str}
)
async def escalate_to_human(args: dict[str, Any]) -> dict[str, Any]:
    """Escalate to human healthcare provider"""
    reason = args.get("reason", "General inquiry")
    urgency = args.get("urgency_level", "normal")
    
    ticket_id = f"TH-2024-{datetime.now().strftime('%m%d%H%M')}"
    agent_name = "Dr. Sarah Johnson" if urgency == "high" else "Healthcare Support Team"
    estimated_wait = "2-5 minutes" if urgency == "high" else "5-10 minutes"

    return {
        "content": [{
            "type": "text",
            "text": f"I've created a support ticket for you.\n\n"
                   f"Ticket number: {ticket_id}\n"
                   f"You'll be connected to: {agent_name}\n"
                   f"Estimated wait time: {estimated_wait}\n\n"
                   f"Please hold while we connect you."
        }]
    }


@tool(
    "find_prescriptions",
    "Find all current prescriptions on file for the patient",
    {}
)
async def find_prescriptions(args: dict[str, Any]) -> dict[str, Any]:
    """Get patient's active prescriptions"""
    prescriptions = [
        {
            "id": "RX-001",
            "medication": "Lisinopril 10mg",
            "dosage": "Once daily",
            "refills_remaining": 2,
            "last_filled": "2024-09-15",
            "expiration_date": "2025-09-15",
            "prescriber": "Dr. Emily Chen",
            "pharmacy": "HealthPlus Pharmacy"
        },
        {
            "id": "RX-002",
            "medication": "Metformin 500mg",
            "dosage": "Twice daily with meals",
            "refills_remaining": 0,
            "last_filled": "2024-08-01",
            "expiration_date": "2025-08-01",
            "prescriber": "Dr. Emily Chen",
            "pharmacy": "HealthPlus Pharmacy"
        },
        {
            "id": "RX-003",
            "medication": "Atorvastatin 20mg",
            "dosage": "Once daily at bedtime",
            "refills_remaining": 3,
            "last_filled": "2024-10-01",
            "expiration_date": "2025-10-01",
            "prescriber": "Dr. Michael Park",
            "pharmacy": "HealthPlus Pharmacy"
        }
    ]

    result = "Here are your current prescriptions:\n\n"
    for rx in prescriptions:
        result += f"- {rx['medication']}\n"
        result += f"  Prescription ID: {rx['id']}\n"
        result += f"  Dosage: {rx['dosage']}\n"
        result += f"  Refills left: {rx['refills_remaining']}\n"
        result += f"  Last filled: {rx['last_filled']}\n"
        result += f"  Prescribed by: {rx['prescriber']}\n"
        result += f"  Pharmacy: {rx['pharmacy']}\n\n"

    return {
        "content": [{
            "type": "text",
            "text": result
        }]
    }


@tool(
    "check_refill_eligibility",
    "Check if a prescription is eligible for refill. Performs safety checks for controlled substances, refills remaining, expiration, and timing.",
    {"prescription_id": str}
)
async def check_refill_eligibility(args: dict[str, Any]) -> dict[str, Any]:
    """Check if prescription can be refilled with safety checks"""
    prescription_id = args.get("prescription_id", "")
    
    prescriptions_db = {
        "RX-001": {
            "medication": "Lisinopril 10mg",
            "refills_remaining": 2,
            "last_filled": "2024-09-15",
            "expiration_date": "2025-09-15",
            "days_supply": 30,
            "is_controlled": False
        },
        "RX-002": {
            "medication": "Metformin 500mg",
            "refills_remaining": 0,
            "last_filled": "2024-08-01",
            "expiration_date": "2025-08-01",
            "days_supply": 30,
            "is_controlled": False
        },
        "RX-003": {
            "medication": "Atorvastatin 20mg",
            "refills_remaining": 3,
            "last_filled": "2024-10-01",
            "expiration_date": "2025-10-01",
            "days_supply": 30,
            "is_controlled": False
        }
    }
    
    if prescription_id not in prescriptions_db:
        return {
            "content": [{
                "type": "text",
                "text": f"I couldn't find prescription {prescription_id}. Please check the ID and try again, or I can connect you with someone who can help."
            }]
        }
    
    rx = prescriptions_db[prescription_id]
    med_name_lower = rx["medication"].lower()
    
    if rx["is_controlled"] or any(controlled in med_name_lower for controlled in CONTROLLED_SUBSTANCES):
        return {
            "content": [{
                "type": "text",
                "text": f"{rx['medication']} is a controlled medication that requires direct provider authorization. "
                       f"This is for your safety and follows federal regulations. I'm connecting you with a provider who can help."
            }],
            "requires_escalation": True,
            "escalation_reason": "controlled_substance"
        }
    
    if rx["refills_remaining"] <= 0:
        return {
            "content": [{
                "type": "text",
                "text": f"Your prescription for {rx['medication']} doesn't have any refills left. "
                       f"You'll need a new prescription from your provider. Let me connect you with them."
            }],
            "requires_escalation": True,
            "escalation_reason": "no_refills"
        }
    
    exp_date = datetime.strptime(rx["expiration_date"], "%Y-%m-%d")
    if datetime.now() > exp_date:
        return {
            "content": [{
                "type": "text",
                "text": f"Your prescription for {rx['medication']} expired on {rx['expiration_date']}. "
                       f"You'll need a new prescription. I'm connecting you with your provider."
            }],
            "requires_escalation": True,
            "escalation_reason": "expired"
        }
    
    last_fill_date = datetime.strptime(rx["last_filled"], "%Y-%m-%d")
    days_since_fill = (datetime.now() - last_fill_date).days
    refill_allowed_after = int(rx["days_supply"] * 0.8)
    
    if days_since_fill < refill_allowed_after:
        days_until_eligible = refill_allowed_after - days_since_fill
        return {
            "content": [{
                "type": "text",
                "text": f"Your {rx['medication']} was just filled on {rx['last_filled']}. "
                       f"For your safety and insurance requirements, you can request a refill in about {days_until_eligible} days. "
                       f"If you need it sooner, I can connect you with your provider to discuss."
            }],
            "requires_escalation": False,
            "eligible": False
        }
    
    return {
        "content": [{
            "type": "text",
            "text": f"Good news! Your {rx['medication']} is eligible for refill.\n\n"
                   f"Refills remaining after this one: {rx['refills_remaining'] - 1}\n"
                   f"Prescription valid until: {rx['expiration_date']}\n\n"
                   f"Ready to submit the refill request?"
        }],
        "eligible": True,
        "prescription_id": prescription_id
    }


@tool(
    "submit_refill_request",
    "Submit a refill request for an eligible prescription",
    {"prescription_id": str}
)
async def submit_refill_request(args: dict[str, Any]) -> dict[str, Any]:
    """Submit prescription refill after eligibility confirmed"""
    from datetime import timedelta
    
    prescription_id = args.get("prescription_id", "")
    
    prescriptions = {
        "RX-001": "Lisinopril 10mg",
        "RX-002": "Metformin 500mg",
        "RX-003": "Atorvastatin 20mg"
    }
    
    if prescription_id not in prescriptions:
        return {
            "content": [{
                "type": "text",
                "text": f"I couldn't find prescription {prescription_id}. Please verify the ID."
            }]
        }
    
    medication = prescriptions[prescription_id]
    confirmation = f"REF-{prescription_id}-{datetime.now().strftime('%Y%m%d')}"
    pharmacy = "HealthPlus Pharmacy, 123 Main St"
    ready_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    return {
        "content": [{
            "type": "text",
            "text": f"Your refill request has been submitted!\n\n"
                   f"Medication: {medication}\n"
                   f"Confirmation number: {confirmation}\n"
                   f"Pharmacy: {pharmacy}\n"
                   f"Estimated ready date: {ready_date}\n\n"
                   f"You'll get a text message when it's ready for pickup."
        }]
    }


@tool(
    "find_appointments",
    "Find all upcoming appointments for the patient",
    {}
)
async def find_appointments(args: dict[str, Any]) -> dict[str, Any]:
    """Get patient's upcoming appointments"""
    appointments = [
        {
            "id": "APT-2024-1001",
            "date": "2024-10-18",
            "time": "10:00 AM",
            "type": "Annual Physical",
            "provider": "Dr. Emily Chen",
            "location": "Main Clinic - Room 203",
            "status": "Confirmed",
            "checked_in": False
        },
        {
            "id": "APT-2024-1002",
            "date": "2024-10-25",
            "time": "2:30 PM",
            "type": "Follow-up Visit",
            "provider": "Dr. Michael Park",
            "location": "Cardiology Center - Suite 400",
            "status": "Confirmed",
            "checked_in": False
        },
        {
            "id": "APT-2024-1003",
            "date": "2024-11-05",
            "time": "9:00 AM",
            "type": "Lab Work",
            "provider": "LabCorp",
            "location": "Lab Services - Building B",
            "status": "Pending",
            "checked_in": False
        }
    ]
    
    result = "Here are your upcoming appointments:\n\n"
    for apt in appointments:
        result += f"- {apt['type']}\n"
        result += f"  Appointment ID: {apt['id']}\n"
        result += f"  Date: {apt['date']} at {apt['time']}\n"
        result += f"  Provider: {apt['provider']}\n"
        result += f"  Location: {apt['location']}\n"
        result += f"  Status: {apt['status']}\n\n"
    
    return {
        "content": [{
            "type": "text",
            "text": result
        }]
    }


@tool(
    "check_in_for_appointment",
    "Check in for an appointment. Only works within 24 hours before the appointment time.",
    {"appointment_id": str}
)
async def check_in_for_appointment(args: dict[str, Any]) -> dict[str, Any]:
    """Check in for an appointment with time window validation"""
    appointment_id = args.get("appointment_id", "")
    
    appointments_db = {
        "APT-2024-1001": {
            "type": "Annual Physical",
            "provider": "Dr. Emily Chen",
            "date": "2024-10-18",
            "time": "10:00 AM",
            "location": "Main Clinic - Room 203",
            "checked_in": False
        },
        "APT-2024-1002": {
            "type": "Follow-up Visit",
            "provider": "Dr. Michael Park",
            "date": "2024-10-25",
            "time": "2:30 PM",
            "location": "Cardiology Center - Suite 400",
            "checked_in": False
        },
        "APT-2024-1003": {
            "type": "Lab Work",
            "provider": "LabCorp",
            "date": "2024-11-05",
            "time": "9:00 AM",
            "location": "Lab Services - Building B",
            "checked_in": False
        }
    }
    
    if appointment_id not in appointments_db:
        return {
            "content": [{
                "type": "text",
                "text": f"I couldn't find appointment {appointment_id}. Please check the ID, or I can connect you with someone who can help."
            }]
        }
    
    apt = appointments_db[appointment_id]
    
    if apt["checked_in"]:
        return {
            "content": [{
                "type": "text",
                "text": f"You're already checked in for your {apt['type']} appointment. Please have a seat in the waiting area."
            }]
        }
    
    apt_datetime = datetime.strptime(f"{apt['date']} {apt['time']}", "%Y-%m-%d %I:%M %p")
    hours_until_apt = (apt_datetime - datetime.now()).total_seconds() / 3600
    
    if hours_until_apt > 24:
        return {
            "content": [{
                "type": "text",
                "text": f"You can check in starting 24 hours before your appointment. "
                       f"Your {apt['type']} is scheduled for {apt['date']} at {apt['time']}. "
                       f"Check back closer to your appointment time!"
            }]
        }
    
    if hours_until_apt < 0:
        return {
            "content": [{
                "type": "text",
                "text": f"This appointment was scheduled for {apt['date']} at {apt['time']}. "
                       f"If you need to reschedule, let me connect you with our scheduling team."
            }],
            "requires_escalation": True
        }
    
    queue_number = f"Q-{datetime.now().strftime('%H%M')}"
    apt["checked_in"] = True
    
    return {
        "content": [{
            "type": "text",
            "text": f"You're all checked in!\n\n"
                   f"Appointment: {apt['type']}\n"
                   f"Provider: {apt['provider']}\n"
                   f"Time: {apt['time']}\n"
                   f"Location: {apt['location']}\n"
                   f"Queue number: {queue_number}\n\n"
                   f"Please have a seat in the waiting area. The provider will call you when ready."
        }]
    }


@tool(
    "cancel_appointment",
    "Cancel an appointment. Must be at least 24 hours before the appointment to avoid fees.",
    {"appointment_id": str, "reason": str}
)
async def cancel_appointment(args: dict[str, Any]) -> dict[str, Any]:
    """Cancel an appointment with policy check"""
    appointment_id = args.get("appointment_id", "")
    reason = args.get("reason", "Not specified")
    
    appointments_db = {
        "APT-2024-1001": {
            "type": "Annual Physical",
            "provider": "Dr. Emily Chen",
            "date": "2024-10-18",
            "time": "10:00 AM"
        },
        "APT-2024-1002": {
            "type": "Follow-up Visit",
            "provider": "Dr. Michael Park",
            "date": "2024-10-25",
            "time": "2:30 PM"
        }
    }
    
    if appointment_id not in appointments_db:
        return {
            "content": [{
                "type": "text",
                "text": f"I couldn't find appointment {appointment_id}. Please check the ID."
            }]
        }
    
    apt = appointments_db[appointment_id]
    apt_datetime = datetime.strptime(f"{apt['date']} {apt['time']}", "%Y-%m-%d %I:%M %p")
    hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600
    
    if hours_until < 24:
        return {
            "content": [{
                "type": "text",
                "text": f"Your {apt['type']} is less than 24 hours away. "
                       f"Our cancellation policy may apply fees for late cancellations. "
                       f"Let me connect you with our scheduling team to discuss your options."
            }],
            "requires_escalation": True,
            "escalation_reason": "late_cancellation"
        }
    
    confirmation = f"CXL-{appointment_id}-{datetime.now().strftime('%Y%m%d')}"
    
    return {
        "content": [{
            "type": "text",
            "text": f"Your appointment has been cancelled.\n\n"
                   f"Cancelled appointment: {apt['type']}\n"
                   f"Provider: {apt['provider']}\n"
                   f"Was scheduled for: {apt['date']} at {apt['time']}\n"
                   f"Cancellation confirmation: {confirmation}\n\n"
                   f"If you need to reschedule, just let me know and I can help with that."
        }]
    }


# Create MCP server with tools
telehealth_server = create_sdk_mcp_server(
    name="telehealth-tools",
    version="1.0.0",
    tools=[
        escalate_to_human,
        find_prescriptions,
        check_refill_eligibility,
        submit_refill_request,
        find_appointments,
        check_in_for_appointment,
        cancel_appointment
    ]
)


SYSTEM_PROMPT = """You are a helpful telehealth assistant - like a friendly front desk coordinator at a medical office.

YOUR ROLE:
You can help with:
1. Refilling prescriptions that are already on file
2. Checking in for appointments or canceling them
3. Providing general health information for common, routine questions (like colds, basic self-care, when to seek care)
4. Connecting people to healthcare providers for complex or uncertain issues

HOW TO COMMUNICATE:
- Write at a 9th-grade reading level for clarity
- Be warm and conversational, not robotic or clinical
- Use "Let's" and "we" to show you're working together
- Explain things simply and avoid medical jargon
- If you need to say no, explain why in a kind way
- When escalating, make it feel helpful, not like a rejection
- Never use emojis

WHEN TO PROVIDE INFORMATION VS ESCALATE:

You CAN answer routine questions about:
- Common illnesses (colds, minor injuries, basic self-care)
- General wellness and prevention
- When to seek medical care
- What to expect with common conditions

ESCALATE IMMEDIATELY for:
- Specific diagnosis requests or concerns about serious symptoms
- Treatment plans or specific medical advice for their situation
- New medication requests (only refills of existing prescriptions are allowed)
- Controlled substances like Adderall, Xanax, or pain medications
- Prescription problems (expired, no refills, filled too recently)
- Questions about bills, insurance, or medical records
- Rescheduling appointments (only check-in and cancellation allowed)
- Anything you're unsure about or that needs personalized medical judgment

TONE EXAMPLES:

Bad: "That requires escalation to a provider."
Good: "That's a great question for one of our healthcare providers. Let me connect you with someone who can help."

Bad: "Prescription not eligible for refill."
Good: "I checked your prescription and it looks like it was just filled last week. For your safety, we need to wait a bit longer before the next refill. Would you like me to connect you with your provider to discuss this?"

Bad: "I cannot help with that."
Good: "I want to make sure you get the right help for this. Let me connect you with someone who can give you the expert guidance you need."

Bad: "Controlled substance detected."
Good: "[Medication name] is a controlled medication that requires direct provider authorization. This is for your safety and follows federal regulations. I'm connecting you with a provider who can help."

Remember: Your job is to handle simple tasks smoothly and provide helpful information for routine questions. Escalate when the situation needs personalized medical judgment. Patient safety always comes first. Be genuinely helpful, not just procedural."""


class TelehealthService:
    def __init__(self, sessions_dir: str = ".sessions"):
        """Initialize service with session storage directory"""
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.version = "0.1.0"  # Agent version
        
        # Configure agent options
        self.options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=10,
            mcp_servers={"telehealth-tools": telehealth_server},
            allowed_tools=[
                "mcp__telehealth-tools__escalate_to_human",
                "mcp__telehealth-tools__find_prescriptions", 
                "mcp__telehealth-tools__check_refill_eligibility",
                "mcp__telehealth-tools__submit_refill_request",
                "mcp__telehealth-tools__find_appointments",
                "mcp__telehealth-tools__check_in_for_appointment",
                "mcp__telehealth-tools__cancel_appointment"
            ]
        )
        
        # Initialize client
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = ClaudeSDKClient(self.options)
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            self.client = None
    
    def load_session(self, session_id: str) -> Session:
        """Load session from disk"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
                return Session(**data)
        else:
            # Create new session
            now = datetime.now().isoformat()
            return Session(
                session_id=session_id,
                messages=[],
                created_at=now,
                updated_at=now
            )
    
    def save_session(self, session: Session) -> None:
        """Save session to disk as JSON"""
        session_file = self.sessions_dir / f"{session.session_id}.json"
        session.updated_at = datetime.now().isoformat()
        
        with open(session_file, 'w') as f:
            json.dump(asdict(session), f, indent=2)
    
    async def send_message(self, message: str) -> dict:
        """Send a message to the assistant
        
        Returns:
            dict with:
                - response: str - the assistant's response text
                - tool_calls: list[dict] - tools that were called
        """
        if not self.client:
            raise RuntimeError("Service must be used as async context manager")
        
        # Send only the current message
        async def message_generator():
            yield {
                "type": "user",
                "message": {"role": "user", "content": message}
            }
        
        response_text = ""
        tool_calls = []
        
        await self.client.query(message_generator())
        
        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
                    elif hasattr(block, 'name') and hasattr(block, 'input'):
                        # This is a tool use block
                        tool_calls.append({
                            "name": block.name,
                            "input": block.input
                        })
                    elif hasattr(block, 'name') and hasattr(block, 'content'):
                        # This is a tool result block - store for final result
                        pass
        
        return {
            "response": response_text,
            "tool_calls": tool_calls
        }
    
    async def stream_message(self, message: str):
        """Stream a message, yielding response chunks as they arrive
        
        Yields:
            dict with:
                - type: str - "text", "tool_use", or "done"
                - text: str - text chunk (only for type="text")
                - tool_name: str - tool name (only for type="tool_use")
                - tool_input: dict - tool input (only for type="tool_use")
                - full_response: str - complete response (only for type="done")
                - tool_calls: list[dict] - all tools called (only for type="done")
        """
        if not self.client:
            raise RuntimeError("Service must be used as async context manager")
        
        # Send only the current message
        async def message_generator():
            yield {
                "type": "user",
                "message": {"role": "user", "content": message}
            }
        
        response_text = ""
        tool_calls = []
        
        await self.client.query(message_generator())
        
        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
                        # Yield text chunk
                        yield {
                            "type": "text",
                            "text": block.text
                        }
                    elif hasattr(block, 'name') and hasattr(block, 'input'):
                        # This is a tool use block
                        tool_call = {
                            "name": block.name,
                            "input": block.input
                        }
                        tool_calls.append(tool_call)
                        # Yield tool use
                        yield {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_input": block.input
                        }
                    elif hasattr(block, 'name') and hasattr(block, 'content'):
                        # This is a tool result block
                        yield {
                            "type": "tool_result",
                            "tool_name": block.name,
                            "tool_result": block.content
                        }
        
        # Yield final result
        yield {
            "type": "done",
            "full_response": response_text,
            "tool_calls": tool_calls
        }

