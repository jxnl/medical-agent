# Telehealth Agent Design

## Overview
A streamlined telehealth chatbot that handles three core functions:
1. Prescription refills (existing prescriptions only)
2. Appointment management (check-in and cancellation)
3. Escalation to healthcare providers (for everything else)

## Core Philosophy
**Keep it simple, keep it safe.** The bot handles routine tasks efficiently and escalates complex medical situations to qualified healthcare providers immediately.

## Tools (7 Total)

### Escalation (1 tool)
- **escalate_to_human**: Connects users to healthcare providers with reason tracking and urgency levels

### Prescription Refills (3 tools)
- **find_prescriptions**: Shows all active prescriptions on file
- **check_refill_eligibility**: Performs comprehensive safety checks
- **submit_refill_request**: Submits approved refill requests

### Appointments (3 tools)
- **find_appointments**: Lists upcoming appointments
- **check_in_for_appointment**: Check-in with 24-hour window validation
- **cancel_appointment**: Cancel with 24-hour policy enforcement

## Safety Checks

### Prescription Refill Safety
1. **Controlled Substance Detection**
   - Automatically detects DEA-scheduled medications (Adderall, Xanax, etc.)
   - Immediate escalation to provider
   - Explains federal regulations to user

2. **Refills Remaining**
   - Checks if prescription has refills available
   - Escalates if no refills (needs new prescription)

3. **Expiration Check**
   - Validates prescription hasn't expired
   - Escalates for new prescription if expired

4. **Timing Safety**
   - Prevents too-soon refills (80% of days supply rule)
   - Protects against abuse and insurance issues
   - Example: 30-day supply can refill on day 24

### Appointment Safety
1. **Check-in Window**
   - Only allows check-in within 24 hours of appointment
   - Prevents premature or missed appointment check-ins

2. **Duplicate Prevention**
   - Checks if already checked in
   - Prevents confusion and system errors

3. **Cancellation Policy**
   - Enforces 24-hour notice requirement
   - Escalates late cancellations (may incur fees)

## Escalation Triggers

### Auto-Escalate for:
- Any medical questions, symptoms, or health concerns
- Controlled substances (Adderall, Xanax, opioids, etc.)
- New medication requests (not on file)
- Prescription issues (expired, no refills, too soon)
- Billing, insurance, or medical records questions
- Appointment rescheduling (only check-in/cancel allowed)
- Anything outside the three core functions

## Personality & Communication

### Writing Style
- 9th-grade reading level for accessibility
- Warm and conversational, not clinical
- Uses "we" and "let's" for partnership feel
- Explains medical/policy requirements kindly
- No emojis (per user preference)

### Tone Principles
1. **Empathetic Explanations**
   - Bad: "Prescription not eligible"
   - Good: "I checked your prescription and it looks like it was just filled last week. For your safety, we need to wait a bit longer before the next refill."

2. **Helpful Escalation**
   - Bad: "That requires escalation"
   - Good: "That's a great question for one of our healthcare providers. Let me connect you with someone who can help."

3. **Transparent Reasoning**
   - Always explain why something can't be done
   - Frame restrictions as safety measures, not obstacles
   - Example: "Because [medication] is a controlled medication that requires direct provider authorization. This is for your safety and follows federal regulations."

## Workflow Examples

### Successful Refill
```
User: "I need a refill on my Lisinopril"
Bot: Finds prescriptions → Checks eligibility → All clear → Submits refill
Result: Confirmation with ready date and pharmacy info
```

### Controlled Substance
```
User: "Can I get a refill on my Adderall?"
Bot: Detects controlled substance → Explains regulations → Escalates
Result: Connected to provider with ticket number
```

### Too-Soon Refill
```
User: "I need more Metformin"
Bot: Checks eligibility → Last filled 5 days ago (30-day supply)
Result: Explains timing, offers provider connection if urgent
```

### Appointment Check-in
```
User: "I want to check in for my appointment"
Bot: Shows appointments → Gets ID → Validates time window → Checks in
Result: Queue number and waiting instructions
```

### Late Cancellation
```
User: "I need to cancel my appointment tomorrow"
Bot: Checks timing → Less than 24 hours → Explains policy
Result: Escalates to scheduling team
```

## Technical Implementation

### Controlled Substances List
Comprehensive list of DEA-scheduled medications:
- Schedule II: Adderall, Ritalin, Oxycodone, Morphine, Fentanyl
- Schedule III: Vicodin, Tylenol with Codeine
- Schedule IV: Xanax, Ativan, Valium, Ambien

### Date/Time Validation
- Uses Python datetime for accurate time calculations
- 80% refill rule: 30-day supply = refill day 24
- 24-hour windows for check-in and cancellation
- Expired prescription detection

### Mock Data Structure
- Prescriptions: ID, medication, dosage, refills, dates, prescriber
- Appointments: ID, type, provider, location, date/time, status
- Realistic pharmacy and provider information

## Future Enhancements

### If Scope Expands:
1. **Insurance Integration**
   - Check coverage before refill
   - Copay estimates
   - Prior authorization status

2. **Drug Interactions**
   - Check new refills against current medications
   - Allergy verification

3. **Lab Results**
   - View recent lab work
   - Alert if labs needed for medication renewal

4. **Appointment Scheduling**
   - Book new appointments (currently only check-in/cancel)
   - Reschedule capability
   - Available slot searches

5. **Secure Messaging**
   - Send/receive messages from providers
   - Prescription questions via messaging

### Areas to NOT Expand:
- Medical diagnosis or symptom assessment
- Medical advice or treatment recommendations
- Prescription dosage changes
- Emergency triage (always escalate to 911 or ER)

## Key Metrics to Track

### Safety Metrics
- Escalation rate for controlled substances (should be 100%)
- False positive/negative refill eligibility checks
- Late cancellation catch rate

### User Experience
- Average task completion time
- Escalation clarity (user understands why)
- Successful self-service rate (refills, check-ins)

### System Performance
- Tool call accuracy
- Response time for common tasks
- Error rate by tool

## Compliance Considerations

### HIPAA
- All patient data access logged
- Secure communication channels required
- No PHI in error messages or logs

### DEA Regulations
- Controlled substance handling per federal rules
- Provider authorization required
- No automated controlled substance refills

### State Requirements
- Provider licensure matching patient location
- Prescription laws vary by state
- Telehealth regulations compliance

