# P&ID Digital Assistant - Text Query Demo Guide

## Overview
This guide provides proven demo use cases for the **Text Queries (RAG)** feature only, avoiding vision queries which have accuracy issues.

---

## 🎯 Best Demo Use Cases

### 1. **Equipment Information Queries**
Ask about specific equipment by tag number:

**Demo Queries:**
- `What is V-101?`
- `Tell me about PSV-101`
- `What is C-104?`
- `Describe V-102`
- `What is P-103?`

**What You'll Get:**
- Equipment type and description
- Operating conditions (pressure, temperature, capacity)
- Location references (which sheet/page)
- Connected systems

**Example Response for "What is V-101?":**
> "V-101 is a high-pressure separator located on sheet 2. It receives flow from the production header and separates gas and liquid phases..."

---

### 2. **Operating Conditions & Specifications**
Get detailed technical specifications:

**Demo Queries:**
- `What are the operating conditions for C-104?`
- `What is the capacity of the gas compressor?`
- `What is the pressure rating of V-101?`
- `What is the set pressure for PSV-103?`

**What You'll Get:**
- Pressure ratings (e.g., "50 PSIG suction, 350 PSIG discharge")
- Temperature specs (e.g., "70°F at suction, 279.1°F at discharge")
- Flow rates and capacities (e.g., "0.50 MMSCFD")
- Set points for safety valves

**Example Response:**
> "C-104 is a gas compressor with:
> - Capacity: 0.50 MMSCFD (14160 SCMD)
> - Suction: 50 PSIG at 70°F
> - Discharge: 350 PSIG at 279.1°F"

---

### 3. **Safety & Instrumentation**
Query about safety devices and instruments:

**Demo Queries:**
- `What safety devices are on V-101?`
- `Tell me about PSV-101`
- `What is the set pressure for PSV-103?`
- `What shutdown valves are in the system?`
- `What flow instruments are on the export line?`

**What You'll Get:**
- Safety valve (PSV) information and set pressures
- Shutdown valve (SDV) locations
- Instrument tags and types
- Safety interlock information

---

### 4. **System & Flow Destinations**
Ask about connections and destinations:

**Demo Queries:**
- `Where does V-101 discharge to?`
- `What systems are connected to the HP separator?`
- `Where does the export liquid pipeline go?`
- `What feeds the gas compressor?`
- `What are the destinations from V-102?`

**What You'll Get:**
- Downstream equipment connections
- System boundaries and interfaces
- Export destinations
- Recycle/spillback connections

**Example Response:**
> "V-101 (HP separator) has multiple discharge points:
> - Gas phase: to gas compressor
> - Liquid phase: to LP separator
> - Emergency relief: to flare system"

---

### 5. **Maintenance & Service History**
Query equipment maintenance tickets (demo data):

**Demo Queries:**
- `Any recent issues with PSV-101?`
- `Show maintenance history for V-102`
- `What was the last service on C-104?`
- `Are there any open tickets for FT-103A?`

**What You'll Get:**
- Recent maintenance activities
- Open issues and their status
- Service dates
- Corrective actions taken

**Available Equipment with Tickets:**
- PSV-101 (Safety valve actuator issue)
- FT-103A (Flow transmitter calibration)
- V-102 (PSV set point verification)
- V-101 (Level alarm testing)
- C-104 (Vibration sensor alarm)

---

### 6. **Piping & Line Specifications**
Ask about piping and connections:

**Demo Queries:**
- `What is the size of the export liquid pipeline?`
- `What line connects V-101 to the compressor?`
- `What is the flare system connection size?`
- `Tell me about the 6"-A line`

**What You'll Get:**
- Pipe sizes (e.g., "4"-F", "6"-A", "12"-A")
- Line classes and ratings
- Connection points

---

### 7. **Control & Instrumentation**
Query about control systems:

**Demo Queries:**
- `What control valves are on V-101?`
- `What instruments control the separator level?`
- `What pressure instruments are on the compressor?`
- `Tell me about FT-103C`

**What You'll Get:**
- Control valve information (LV, PV, FV)
- Transmitter details (PT, LT, FT)
- Controller references (PIC, LIC, FIC)

---

### 8. **General System Questions**
Broader questions about the facility:

**Demo Queries:**
- `What separators are in this facility?`
- `List all the compressors`
- `What safety valves protect the high pressure system?`
- `What types of pumps are shown?`

**What You'll Get:**
- Equipment inventory
- System overview
- Safety system summary

---

## 🎬 Recommended Demo Flow

### **Scenario 1: New Engineer Onboarding**
1. "What is V-101?" → Get equipment overview
2. "What are the operating conditions for V-101?" → Get technical specs
3. "What safety devices protect V-101?" → Learn safety systems
4. "Any recent maintenance on V-101?" → Check service history

### **Scenario 2: Operations Support**
1. "What is the capacity of C-104?" → Check compressor specs
2. "Where does the gas compressor discharge to?" → Understand flow path
3. "Any recent issues with C-104?" → Check maintenance status
4. "What instruments monitor C-104?" → Identify key measurements

### **Scenario 3: Maintenance Planning**
1. "Tell me about PSV-101" → Equipment details
2. "What is the set pressure for PSV-101?" → Get calibration info
3. "Any recent maintenance on PSV-101?" → See ticket (shows actuator replacement)
4. "What other safety valves are in the system?" → Plan comprehensive testing

---

## ✅ Equipment Tags Available for Demo

### **Vessels:**
- V-101 (HP Separator)
- V-102 (LP Separator)

### **Compressors:**
- C-104 (Gas Compressor - 1st Stage)

### **Pumps:**
- P-103 (Export Liquid Pump)

### **Safety Valves (PSV):**
- PSV-101, PSV-102, PSV-103, PSV-104B

### **Shutdown Valves (SDV):**
- SDV-101, SDV-102A, SDV-102B, SDV-103, SDV-104, SDV-106

### **Flow Instruments:**
- FT-103C, FV-103C, FIC-103C

### **Level Instruments:**
- LT-101A, LT-101B, LT-102A, LT-110
- LV-101, LV-101A
- LIC-101A

### **Pressure Instruments:**
- PT-101B, PT-101D, PT-103B
- PI-101C, PI-103B
- PV-101A, PV-101B
- PIC-101B
- PCV-105B, PCV-105C

---

## ⚠️ What NOT to Demo (Vision Query Issues)

**Avoid these for now:**
- ❌ "Show me where V-101 is on the diagram" (vision hallucination issues)
- ❌ "Count the orifice meters" (vision inaccuracies)
- ❌ "Display the flow path from X to Y" (vision query - unreliable)
- ❌ Questions requiring visual diagram interpretation

**Stick to text-based queries about:**
- ✅ Equipment specifications
- ✅ Operating conditions
- ✅ Connections and destinations
- ✅ Maintenance history
- ✅ System descriptions

---

## 💡 Pro Tips for Successful Demos

1. **Start Simple**: Begin with "What is V-101?" to show basic functionality
2. **Build Complexity**: Progress to operating conditions, then maintenance history
3. **Show Integration**: Demonstrate how ticket system integrates with queries
4. **Highlight Speed**: Emphasize instant answers vs. manual P&ID searching
5. **Emphasize Accuracy**: Point out how answers cite specific equipment tags
6. **Use Real Scenarios**: Frame queries around actual engineering tasks

---

## 📊 Key Metrics to Highlight

- **7 indexed P&ID pages** covering complete process flow
- **Instant retrieval** from vector database
- **Token tracking** showing cost efficiency
- **Gemini Flash Lite** model for fast, cost-effective responses
- **Maintenance integration** with ticket system

---

## 🎓 Sample Demo Script

**Intro:**
> "Let me show you our P&ID Digital Assistant. Instead of manually searching through 6 sheets of P&IDs, you can ask questions in natural language."

**Demo Query 1:**
> "What is V-101?"
> [Show instant response with equipment type, location, and connections]

**Demo Query 2:**
> "What are the operating conditions for C-104?"
> [Show detailed specs: capacity, pressure, temperature]

**Demo Query 3:**
> "Any recent issues with PSV-101?"
> [Show maintenance ticket with service history]

**Conclusion:**
> "This saves engineers hours of manual searching and ensures everyone has instant access to critical equipment information."

---

Generated: 2025-10-21
Version: MVP 1.0
