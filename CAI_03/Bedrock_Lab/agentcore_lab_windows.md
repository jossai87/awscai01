# Amazon Bedrock AgentCore — Step-by-Step Lab (Windows / PowerShell)

> Run each phase sequentially. Each phase builds on the previous one.  
> Copy and paste commands one at a time unless noted otherwise.  
> Open **PowerShell** (not Command Prompt) for all commands.

**First-time setup — allow PowerShell scripts to run:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Latest AgentCore features (April 2026)**
- Managed Agent Harness *(preview)* — stand up an agent in 3 API calls
- AgentCore CLI with hot-reload dev server & browser inspector
- Runtime, Memory, Gateway, Browser, Code Interpreter, Identity, Observability
- VPC / PrivateLink / CloudFormation / resource tagging (GA)
- MCP server integration (works with Kiro, Cursor, Claude Code, Amazon Q CLI)

**Docs:** https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/  
**SDK:** https://github.com/aws/bedrock-agentcore-sdk-python  
**CLI:** https://github.com/aws/agentcore-cli  
**Console:** https://console.aws.amazon.com/bedrock-agentcore/home#

---

## Phase 0 — Prerequisites & Environment Check

Check these one at a time before moving on.

**0.1 — Check Node.js version (must be 20+). If you see v18.x or lower, go to Phase 1 first.**
```powershell
node --version
```

**0.2 — Check Python version (must be 3.10+)**
```powershell
python --version
```

**0.3 — Confirm AWS CLI is configured and can reach AWS**
```powershell
aws sts get-caller-identity
```

**0.4 — Check your default region**
```powershell
aws configure get region
```

**0.5 — (Optional) Set a working region for this session**
```powershell
$env:AWS_DEFAULT_REGION = "us-east-1"
```

---

## Phase 1 — Upgrade Node.js to v20+ and Install the AgentCore CLI

AgentCore requires Node 20+. The recommended Windows approach is **nvm-windows** — it installs Node in your user profile so `npm install -g` never needs admin rights.

> **Note:** nvm-windows is a separate project from the macOS nvm. Same concept, different installer.

### Step A — Install nvm-windows

**1.A.1 — Download and run the nvm-windows installer**

Go to the releases page and download `nvm-setup.exe`:
```
https://github.com/coreybutler/nvm-windows/releases/latest
```

Run the installer, accept the defaults, then **close and reopen PowerShell** before continuing.

**1.A.2 — Verify nvm-windows is available**
```powershell
nvm version
```

### Step B — Install Node 20 LTS

**1.B.1 — Install Node 20 LTS**
```powershell
nvm install 20
```

**1.B.2 — Switch to Node 20**

> Run PowerShell as Administrator for this step.
```powershell
nvm use 20
```

**1.B.3 — Confirm you are now on Node 20+**
```powershell
node --version
npm --version
```

### Step C — Install the AgentCore CLI

**1.C.1 — Install the stable AgentCore CLI globally**
```powershell
npm install -g @aws/agentcore
```

**1.C.2 — Verify the install**
```powershell
agentcore --version
```

> If `agentcore` is not found, refresh your PATH without restarting:
> ```powershell
> $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
> ```

**1.C.3 — (Optional) Install the PREVIEW channel to unlock the Managed Harness**
```powershell
npm install -g @aws/agentcore@preview
```

### Step D — Install Python dependencies

**1.D.1 — Install the AgentCore Python SDK**
```powershell
pip install bedrock-agentcore
```

**1.D.2 — Install Strands Agents framework (recommended by AWS for AgentCore)**
```powershell
pip install strands-agents strands-agents-tools
```

---

## Phase 2 — Scaffold Your First Agent Project

**2.1 — Create a new AgentCore project (interactive wizard)**

The wizard asks: framework, model provider, memory, build type.
```powershell
agentcore create
```

**2.2 — (Alternative) Create with flags to skip the wizard**

> PowerShell uses backtick `` ` `` for line continuation, not `\`
```powershell
agentcore create `
  --name MyBedrockAgent `
  --framework Strands `
  --model-provider Bedrock `
  --memory none `
  --build CodeZip
```

**2.3 — Move into the project directory**
```powershell
Set-Location MyBedrockAgent
```

**2.4 — Review the generated project structure**
```
MyBedrockAgent\
├── agentcore\
│   ├── agentcore.json      <- main config (agents, memory, gateways, etc.)
│   ├── aws-targets.json    <- AWS account + region for deployment
│   └── cdk\                <- CDK infra (auto-managed, don't edit manually)
└── app\
    └── MyBedrockAgent\
        ├── main.py         <- YOUR agent code lives here
        └── pyproject.toml  <- Python dependencies
```

---

## Phase 3 — Run & Test Locally (Hot Reload Dev Server)

**3.1 — Start the local dev server with browser inspector**

Opens `http://localhost:8080` — chat with your agent and inspect traces.
```powershell
agentcore dev
```

**3.2 — (Alternative) Use the terminal TUI instead of the browser**
```powershell
agentcore dev --no-browser
```

**3.3 — (Alternative) Tail server logs in non-interactive mode**
```powershell
agentcore dev --logs
```

**3.4 — (Alternative) Pin the dev port**
```powershell
agentcore dev --port 8080
```

> **Tip:** Edit `app\MyBedrockAgent\main.py` while `agentcore dev` is running — changes are picked up automatically (hot reload).

---

## Phase 4 — Deploy to AWS (AgentCore Runtime)

**4.1 — Preview what will be deployed (dry run — no changes made)**
```powershell
agentcore deploy --plan
```

**4.2 — Deploy your agent to AgentCore Runtime**

First deploy takes a few minutes while CDK bootstraps your account. Subsequent deploys are faster.
```powershell
agentcore deploy
```

**4.3 — Check deployment status**
```powershell
agentcore status
```

**4.4 — Invoke your deployed agent with a test prompt**
```powershell
agentcore invoke --prompt "Hello, what can you do?"
```

**4.5 — Invoke with a session ID (enables multi-turn conversation)**
```powershell
agentcore invoke --prompt "Remember my name is Alex" --session-id my-session-001
```
```powershell
agentcore invoke --prompt "What is my name?" --session-id my-session-001
```

---

## Phase 5 — Add Short-Term Memory

Agents can now remember context within a session.

**5.1 — Add memory to your project (interactive — choose short-term)**
```powershell
agentcore add memory
```

**5.2 — Deploy the memory resource**
```powershell
agentcore deploy
```

**5.3 — Test memory within the same session**
```powershell
agentcore invoke --prompt "My favorite color is blue." --session-id mem-test-001
```
```powershell
agentcore invoke --prompt "What is my favorite color?" --session-id mem-test-001
```

**5.4 — View the memory config that was added to agentcore.json**
```powershell
Get-Content agentcore\agentcore.json
```

---

## Phase 6 — Add Long-Term Memory

Agents can now persist knowledge across sessions.

**6.1 — Add long-term memory (re-run agentcore add memory, choose long-term)**
```powershell
agentcore add memory
```

**6.2 — Deploy**
```powershell
agentcore deploy
```

**6.3 — Test cross-session memory**
```powershell
agentcore invoke --prompt "I work as a data scientist." --session-id lt-session-A
```
```powershell
agentcore invoke --prompt "What do I do for work?" --session-id lt-session-B
```

---

## Phase 7 — Add AgentCore Gateway

Gateway transforms external APIs and Lambda functions into agent-ready tools. This phase walks through the full end-to-end setup: creating the gateway, attaching a real Lambda-backed tool, wiring it into your agent code, and testing it.

### Step A — Create the Gateway

**7.A.1 — Add a gateway via the AgentCore CLI**
```powershell
agentcore add gateway
```

**7.A.2 — Deploy the gateway resource**
```powershell
agentcore deploy
```

**7.A.3 — Capture the Gateway ID from the status output**
```powershell
agentcore status
```

> Copy the `gatewayId` value from the output — you will need it in the steps below. It looks like `gw-xxxxxxxxxxxxxxxxx`.

**7.A.4 — Save the Gateway ID as a variable so you can reuse it**
```powershell
$GATEWAY_ID = "gw-xxxxxxxxxxxxxxxxx"   # replace with your actual ID
```

### Step B — Create a Lambda Function as a Tool

This Lambda will be the actual tool your agent calls through the gateway. It returns a weather summary for a given city (a simple example you can swap out for any real API).

**7.B.1 — Create the Lambda execution role**
```powershell
aws iam create-role `
  --role-name AgentCoreGatewayLambdaRole `
  --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}'
```

**7.B.2 — Attach the basic Lambda execution policy**
```powershell
aws iam attach-role-policy `
  --role-name AgentCoreGatewayLambdaRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**7.B.3 — Create the Lambda function code file**

Create a file called `weather_tool.py` in your temp folder with this content:
```python
import json

def handler(event, context):
    """
    Simple weather tool for AgentCore Gateway.
    Expects: { "city": "Seattle" }
    Returns: a mock weather summary string.
    """
    city = event.get("city", "Unknown")
    # In a real implementation, call a weather API here
    weather_data = {
        "Seattle": "Cloudy, 58F, chance of rain",
        "New York": "Sunny, 72F, clear skies",
        "Austin": "Partly cloudy, 85F, humid",
    }
    summary = weather_data.get(city, f"No data available for {city}")
    return {
        "statusCode": 200,
        "body": json.dumps({"city": city, "weather": summary})
    }
```

Save it to `C:\Temp\weather_tool.py` (create the folder if needed):
```powershell
New-Item -ItemType Directory -Force -Path C:\Temp
```
```powershell
Set-Content -Path C:\Temp\weather_tool.py -Value @'
import json

def handler(event, context):
    city = event.get("city", "Unknown")
    weather_data = {
        "Seattle": "Cloudy, 58F, chance of rain",
        "New York": "Sunny, 72F, clear skies",
        "Austin": "Partly cloudy, 85F, humid",
    }
    summary = weather_data.get(city, f"No data available for {city}")
    return {
        "statusCode": 200,
        "body": __import__("json").dumps({"city": city, "weather": summary})
    }
'@
```

**7.B.4 — Zip the function**
```powershell
Compress-Archive -Path C:\Temp\weather_tool.py -DestinationPath C:\Temp\weather_tool.zip -Force
```

**7.B.5 — Get your AWS account ID**
```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
Write-Host $ACCOUNT_ID
```

**7.B.6 — Deploy the Lambda function**
```powershell
aws lambda create-function `
  --function-name AgentCoreWeatherTool `
  --runtime python3.12 `
  --role "arn:aws:iam::${ACCOUNT_ID}:role/AgentCoreGatewayLambdaRole" `
  --handler weather_tool.handler `
  --zip-file fileb://C:\Temp\weather_tool.zip `
  --timeout 30
```

**7.B.7 — Test the Lambda directly to confirm it works**
```powershell
aws lambda invoke `
  --function-name AgentCoreWeatherTool `
  --payload '{\"city\": \"Seattle\"}' `
  --cli-binary-format raw-in-base64-out `
  C:\Temp\lambda_response.json

Get-Content C:\Temp\lambda_response.json
```

> Expected output: `{"statusCode": 200, "body": "{\"city\": \"Seattle\", \"weather\": \"Cloudy, 58F, chance of rain\"}"}`

### Step C — Register the Lambda as a Gateway Target

**7.C.1 — Get the Lambda ARN**
```powershell
$LAMBDA_ARN = aws lambda get-function `
  --function-name AgentCoreWeatherTool `
  --query 'Configuration.FunctionArn' `
  --output text
Write-Host $LAMBDA_ARN
```

**7.C.2 — Create a gateway target pointing to the Lambda**

> Using a PowerShell here-string for the JSON to avoid escaping issues:
```powershell
$targetConfig = @"
{
  "lambda": {
    "lambdaArn": "$LAMBDA_ARN",
    "toolSchema": {
      "tools": [{
        "toolSpec": {
          "name": "get_weather",
          "description": "Get the current weather for a city",
          "inputSchema": {
            "json": {
              "type": "object",
              "properties": {
                "city": {
                  "type": "string",
                  "description": "The name of the city to get weather for"
                }
              },
              "required": ["city"]
            }
          }
        }
      }]
    }
  }
}
"@

aws bedrock-agentcore-control create-gateway-target `
  --gateway-identifier $GATEWAY_ID `
  --name "weather-tool" `
  --description "Returns current weather for a given city" `
  --target-configuration $targetConfig
```

**7.C.3 — Confirm the target was registered**
```powershell
aws bedrock-agentcore-control list-gateway-targets `
  --gateway-identifier $GATEWAY_ID
```

### Step D — Grant the Gateway Permission to Invoke the Lambda

**7.D.1 — Add a resource-based policy to the Lambda**
```powershell
$REGION = aws configure get region
aws lambda add-permission `
  --function-name AgentCoreWeatherTool `
  --statement-id AgentCoreGatewayInvoke `
  --action lambda:InvokeFunction `
  --principal bedrock-agentcore.amazonaws.com `
  --source-arn "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:gateway/${GATEWAY_ID}"
```

### Step E — Wire the Gateway into Your Agent Code

**7.E.1 — Get the Gateway endpoint URL**
```powershell
$GATEWAY_ENDPOINT = aws bedrock-agentcore-control get-gateway `
  --gateway-identifier $GATEWAY_ID `
  --query 'gatewayUrl' `
  --output text
Write-Host $GATEWAY_ENDPOINT
```

**7.E.2 — Update `app\MyBedrockAgent\main.py` to use the gateway tool**

Replace the contents of `main.py` with the following:
```python
import os
from strands import Agent
from strands.tools.mcp import MCPClient

# Connect to the AgentCore Gateway (exposes your Lambda as an MCP tool)
gateway_url = os.environ.get("AGENTCORE_GATEWAY_URL", "PASTE_YOUR_GATEWAY_ENDPOINT_HERE")

mcp_client = MCPClient(gateway_url)

# Build the agent with the gateway-backed tools
agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt=(
        "You are a helpful assistant with access to real-time tools. "
        "When asked about weather, use the get_weather tool."
    ),
    tools=mcp_client.tools,
)

def handler(event, context=None):
    prompt = event.get("prompt", "Hello!")
    response = agent(prompt)
    return {"response": str(response)}
```

**7.E.3 — Set the gateway URL as an environment variable for local dev**
```powershell
$env:AGENTCORE_GATEWAY_URL = $GATEWAY_ENDPOINT
```

**7.E.4 — Test locally with the gateway connected**
```powershell
agentcore dev
```

### Step F — Deploy and Test End-to-End

**7.F.1 — Deploy the updated agent**
```powershell
agentcore deploy
```

**7.F.2 — Test the gateway tool through your deployed agent**
```powershell
agentcore invoke --prompt "What is the weather in Seattle?"
```
```powershell
agentcore invoke --prompt "Compare the weather in New York and Austin"
```

**7.F.3 — (Optional) Add an MCP server as a second gateway target**
```powershell
aws bedrock-agentcore-control create-gateway-target `
  --gateway-identifier $GATEWAY_ID `
  --name "my-mcp-server" `
  --target-configuration '{\"mcp\":{\"endpoint\":\"https://your-mcp-server.example.com\"}}'
```

---

## Phase 8 — Add AgentCore Code Interpreter

Gives your agent a sandboxed Python execution environment.

**8.1 — Install the Strands tools package (includes code interpreter client)**
```powershell
pip install strands-agents-tools
```

**8.2 — Create a Code Interpreter resource**
```powershell
aws bedrock-agentcore-control create-code-interpreter `
  --name "MyCodeInterpreter" `
  --network-configuration '{\"networkMode\": \"PUBLIC\"}'
```

**8.3 — Add the code interpreter tool to `app\MyBedrockAgent\main.py`**
```python
from strands import Agent
from strands_tools import code_interpreter

agent = Agent(tools=[code_interpreter])

def handler(event, context=None):
    prompt = event.get("prompt", "Hello!")
    response = agent(prompt)
    return {"response": str(response)}
```

**8.4 — Deploy with code interpreter enabled**
```powershell
agentcore deploy
```

**8.5 — Test code execution**
```powershell
agentcore invoke --prompt "Write Python code to calculate the first 10 Fibonacci numbers and run it"
```

---

## Phase 9 — Add AgentCore Browser

Gives your agent a managed web browser for web automation.

**9.1 — Create a Browser resource**
```powershell
aws bedrock-agentcore-control create-browser `
  --name "MyAgentBrowser" `
  --network-configuration '{\"networkMode\": \"PUBLIC\"}'
```

**9.2 — Add the browser tool to `app\MyBedrockAgent\main.py`**
```python
from strands import Agent
from strands_tools import browser_tool

agent = Agent(tools=[browser_tool])

def handler(event, context=None):
    prompt = event.get("prompt", "Hello!")
    response = agent(prompt)
    return {"response": str(response)}
```

**9.3 — Deploy**
```powershell
agentcore deploy
```

**9.4 — Test browser automation**
```powershell
agentcore invoke --prompt "Go to https://aws.amazon.com and tell me the main headline"
```

---

## Phase 10 — Add AgentCore Identity (OAuth / API Key Credentials)

Lets your agent securely access third-party services like GitHub, Slack, etc.

**10.1 — Add a credential provider (interactive)**
```powershell
agentcore add credential
```

**10.2 — Store a GitHub API key in AWS Secrets Manager**
```powershell
aws secretsmanager create-secret `
  --name /agentcore/credentials/github `
  --secret-string '{\"api_key\": \"ghp_YOUR_TOKEN_HERE\"}'
```

**10.3 — Register the credential with AgentCore**
```powershell
agentcore add credential `
  --name github-token `
  --type api-key `
  --secret-name /agentcore/credentials/github
```

**10.4 — Deploy with identity configured**
```powershell
agentcore deploy
```

**10.5 — Test that your agent can authenticate to the external service**
```powershell
agentcore invoke --prompt "List my GitHub repositories"
```

---

## Phase 11 — Enable Observability (Traces, Logs, Metrics in CloudWatch)

**11.1 — Add an evaluator / observability config**
```powershell
agentcore add evaluator
```

**11.2 — Deploy with observability enabled**
```powershell
agentcore deploy
```

**11.3 — Invoke your agent to generate trace data**
```powershell
agentcore invoke --prompt "Summarize the latest AWS news"
```

**11.4 — Tail CloudWatch logs for your agent runtime**

Replace `<RUNTIME_ID>` with the ID shown in `agentcore status`.
```powershell
aws logs tail /aws/bedrock-agentcore/runtime/<RUNTIME_ID> --follow
```

**11.5 — Open the AgentCore console in your browser**
```powershell
Start-Process "https://console.aws.amazon.com/bedrock-agentcore/home#"
```

---

## Phase 12 — Add a Second Agent (Multi-Agent Project)

**12.1 — Add a second agent to the same project**
```powershell
agentcore add agent
```

**12.2 — Deploy both agents**
```powershell
agentcore deploy
```

**12.3 — Invoke the second agent by name**
```powershell
agentcore invoke --agent SecondAgent --prompt "What is your specialty?"
```

**12.4 — Check status of all agents in the project**
```powershell
agentcore status
```

---

## Phase 13 — [Preview] Managed Harness (Zero-Code Agent in 3 API Calls)

> Requires the preview CLI: `npm install -g @aws/agentcore@preview`  
> Declare your agent in a config file — no framework, no orchestration code needed.

**13.1 — Install the preview CLI**
```powershell
npm install -g @aws/agentcore@preview
```

**13.2 — Create a harness-based agent project**

When the wizard asks for agent type, choose **Managed Harness**.
```powershell
agentcore create
```

**13.3 — The generated `agentcore.json` will look like this**
```json
{
  "agents": [{
    "name": "HarnessAgent",
    "type": "harness",
    "model": "us.amazon.nova-pro-v1:0",
    "systemPrompt": "You are a helpful assistant.",
    "tools": ["code_interpreter", "browser"],
    "memory": { "strategy": "FULL_CONVERSATION" }
  }]
}
```

**13.4 — Deploy — no Python code to write, AgentCore runs the loop for you**
```powershell
agentcore deploy
```

**13.5 — Invoke the harness agent**
```powershell
agentcore invoke --prompt "Analyze this CSV data and create a summary"
```

---

## Phase 14 — VPC / PrivateLink (Enterprise Security)

Deploy your agent inside a VPC for network isolation.

**14.1 — Add VPC configuration to your project**
```powershell
agentcore add vpc
```

**14.2 — Deploy with VPC networking**
```powershell
agentcore deploy
```

**14.3 — Verify the runtime is in your VPC**
```powershell
agentcore status
```

---

## Phase 15 — Cleanup

Remove all deployed resources to avoid ongoing charges.

**15.1 — Preview what will be destroyed (dry run)**
```powershell
agentcore destroy --plan
```

**15.2 — Destroy all AgentCore resources for this project**
```powershell
agentcore destroy
```

**15.3 — Delete the Lambda function created in Phase 7**
```powershell
aws lambda delete-function --function-name AgentCoreWeatherTool
```

**15.4 — Delete the IAM role created in Phase 7**
```powershell
aws iam detach-role-policy `
  --role-name AgentCoreGatewayLambdaRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam delete-role --role-name AgentCoreGatewayLambdaRole
```

**15.5 — Verify everything is cleaned up**
```powershell
agentcore status
```

**15.6 — (Optional) Remove the AgentCore CLI**
```powershell
npm uninstall -g @aws/agentcore
```

---

## Windows-Specific Notes

| Topic | Detail |
|---|---|
| Line continuation | Use backtick `` ` `` not backslash `\` |
| JSON in AWS CLI | Escape quotes: `{\"key\": \"value\"}` or use a here-string `@" ... "@` |
| Read a file | `Get-Content filename` instead of `cat` |
| Change directory | `Set-Location path` or `cd path` |
| PATH not updated | Run the PATH refresh command from Phase 1.C.2 |
| Open a URL | `Start-Process "https://..."` |

---

## Quick Reference

| Command | What it does |
|---|---|
| `agentcore create` | Scaffold a new agent project |
| `agentcore dev` | Local dev server with hot reload + browser inspector |
| `agentcore deploy --plan` | Preview changes before deploying |
| `agentcore deploy` | Deploy to AWS |
| `agentcore invoke` | Test your deployed agent |
| `agentcore status` | Check deployment status |
| `agentcore add memory` | Add short/long-term memory |
| `agentcore add gateway` | Connect external APIs / MCP servers |
| `agentcore add credential` | Add OAuth / API key for third-party services |
| `agentcore add evaluator` | Enable observability |
| `agentcore add agent` | Add a second agent to the project |
| `agentcore destroy` | Tear down all resources |
