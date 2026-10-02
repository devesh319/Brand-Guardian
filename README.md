# Brand Guardian

Brand Guardian audits YouTube videos against a curated compliance knowledge base. It downloads a submitted video, extracts its transcript and on-screen text with Azure Video Indexer, retrieves relevant policy material from Azure AI Search, and uses Azure OpenAI to produce a `PASS` or `FAIL` assessment with any detected issues.

The project provides both a command-line workflow and a FastAPI service. Completed audits are cached locally in SQLite by their exact video URL.

> **Important:** This tool is an assistive compliance review system, not legal advice or a substitute for human approval. Review all findings against your organisation's current policies before making a publishing decision.

## Capabilities

- Accepts public YouTube URLs (`youtube.com` and `youtu.be`).
- Downloads and indexes video content through Azure Video Indexer.
- Evaluates transcripts and OCR-derived on-screen text against PDF policy documents.
- Uses retrieval-augmented generation (RAG) with Azure AI Search and Azure OpenAI.
- Returns a structured list of issues, a summary report, and a `PASS` or `FAIL` status.
- Exposes the workflow through a CLI and a FastAPI endpoint.
- Persists completed analyses in a local SQLite database and can emit Azure Monitor telemetry.

## Architechture

<img width="26863" height="15891" alt="bg-arch" src="https://github.com/user-attachments/assets/378181b6-d25e-4d33-8fe4-a6c37163ca3b" />



## Prerequisites

- Python 3.14 or later (as declared in `pyproject.toml`)
- [uv](https://docs.astral.sh/uv/) for dependency and environment management
- An Azure subscription with access to:
  - Azure Video Indexer
  - Azure OpenAI (chat and embedding deployments)
  - Azure AI Search with vector search enabled
- An Azure identity that can generate Azure Video Indexer account tokens. For local development, sign in with `az login`; in Azure, use a managed identity or another credential source supported by `DefaultAzureCredential`.

You must have permission to download, process, and retain every video submitted to the service. YouTube availability, regional restrictions, copyright controls, and Azure Video Indexer policies can prevent a video from being processed.

## Quick start

1. Clone the repository and change into it.

   ```bash
   git clone <repository-url>
   cd CompilanceQAPipeline
   ```

2. Create the environment and install dependencies.

   ```bash
   uv sync
   ```

3. Create a `.env` file in the repository root using the configuration below.

4. Create the local audit-results table.

   ```bash
   uv run python backend/scripts/create_database.py
   ```

5. Place the compliance PDFs to use for auditing in `backend/data/`, then create or populate the Azure AI Search index.

   ```bash
   uv run python backend/scripts/index_documents.py
   ```

6. Run an audit from the command line or start the API, as described in [Run an audit](#run-an-audit).

Run the database setup and document-indexing steps before the first audit. Re-run the indexing command after changing the policy documents.

## Configuration

Create a `.env` file in the project root. Replace every placeholder with the value for your Azure resources; do not commit this file.

```dotenv
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<openai-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<openai-api-key>
AZURE_OPENAI_API_VERSION=<api-version>
AZURE_OPENAI_CHAT_DEPLOYMENT=<chat-deployment-name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<embedding-deployment-name>

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<search-admin-key>
AZURE_SEARCH_INDEX_NAME=<compliance-rules-index>

# Azure Video Indexer
AZURE_VI_ACCOUNT_ID=<video-indexer-account-id>
AZURE_VI_LOCATION=<azure-region>
AZURE_VI_SUBSCRIPTION_ID=<subscription-id>
AZURE_VI_RESOURCE_GROUP=<resource-group-name>
AZURE_VI_NAME=<video-indexer-account-name>

# Optional: Azure Monitor / Application Insights telemetry (API only)
APPLICATION_INSIGHTS_CONNECTION_STRING=<application-insights-connection-string>
```

| Setting | Required | Used for |
| --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | Creating embeddings while indexing the policy PDFs and Azure OpenAI client discovery. |
| `AZURE_OPENAI_API_KEY` | Yes | Authenticating to Azure OpenAI. |
| `AZURE_OPENAI_API_VERSION` | Yes | Azure OpenAI API version. |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Yes | The chat deployment that performs the audit. |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes | The embedding deployment used to index the policy PDFs. |
| `AZURE_SEARCH_ENDPOINT` | Yes | Azure AI Search service endpoint. |
| `AZURE_SEARCH_API_KEY` | Yes | Authenticating to Azure AI Search. |
| `AZURE_SEARCH_INDEX_NAME` | Yes | Vector index containing the compliance-policy chunks. |
| `AZURE_VI_*` | Yes | Locating the Azure Video Indexer account and generating account access tokens. |
| `APPLICATION_INSIGHTS_CONNECTION_STRING` | No | Enabling Azure Monitor telemetry for the API. |

For the audit workflow to retrieve documents consistently, use the same embedding model and compatible vector dimensions when indexing and querying. The current audit node has `text-embedding-3-small` hard-coded for retrieval; set `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` to the corresponding deployment before indexing, or align the implementation before using another embedding model.

Keep secrets out of source control, terminals, and logs. For deployed environments, use a managed secret store and workload identity instead of a checked-in `.env` file.

## Knowledge base

The default policy corpus is stored in `backend/data/` and currently includes PDF documents. The indexing script:

1. Loads every `*.pdf` file in that directory.
2. Splits the content into 1,000-character chunks with 200 characters of overlap.
3. Creates embeddings and uploads the chunks to the configured Azure AI Search index.

The auditor retrieves the three most similar chunks for each video. Audit quality therefore depends on the accuracy, currency, and coverage of the documents in the index. Re-index only approved policy material and maintain an external change-control process for it.

## Run an audit

### Command line

```bash
uv run python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

Use `--url` (or `-u`) with a supported YouTube URL. The command prints the video ID, final status, detected violations, and final report.

### API

Start the development server:

```bash
uv run uvicorn backend.src.api.server:app --reload
```

Interactive OpenAPI documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns the service health payload. |
| `POST` | `/audit` | Runs or returns a cached compliance audit for a video URL. |

Submit an audit:

```bash
curl --request POST http://127.0.0.1:8000/audit \
  --header "Content-Type: application/json" \
  --data '{"video_url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Successful responses contain a session identifier, a video identifier, the final status, a narrative report, and any issues found:

```json
{
  "session_id": "...",
  "video_id": "vid_...",
  "status": "PASS",
  "final_report": "No violations found in the retrieved policy scope.",
  "compliance_results": []
}
```

Each item in `compliance_results` has `category`, `severity`, and `description` fields. An audit is synchronous: the API call remains open while the video is downloaded, processed by Azure Video Indexer, and evaluated. Configure an appropriate upstream timeout before exposing it behind a gateway.

## Data, caching, and observability

- Audit outputs are stored in `brand_guardian.db` at the repository root. The cache key is the exact submitted video URL, so different URL forms for the same video are treated separately.
- Stored data includes the URL, video metadata, transcript, OCR text, compliance results, status, and report. Treat the database as potentially sensitive data and protect it accordingly.
- When the API runs, it writes application logs to `logs/`. Set `APPLICATION_INSIGHTS_CONNECTION_STRING` to also configure Azure Monitor telemetry.
- A processing, retrieval, model, or transcription failure currently produces a `FAIL` status. Consumers should distinguish technical errors from confirmed policy violations by checking the returned report and error context.

### Current portability note

`main.py` and `backend/src/api/server.py` currently set `DB_PATH` to the original developer's absolute workspace path. After cloning to a different location, update those constants to your local `brand_guardian.db` path (or refactor them to use a project-relative path) before running the CLI or API. The database-creation script itself creates the file at the repository root.

## Project layout

```text
.
├── backend/
│   ├── data/                 # Compliance-policy PDFs to index
│   ├── scripts/              # Database creation and document-indexing commands
│   ├── src/
│   │   ├── api/              # FastAPI service and telemetry setup
│   │   ├── graph/            # LangGraph state, nodes, and workflow
│   │   └── services/         # Azure Video Indexer integration
│   └── utils/                # SQLite persistence and CLI output helpers
├── main.py                   # CLI entry point
├── pyproject.toml            # Project metadata and dependencies
└── README.md
```

## Production considerations

- The API has no authentication or authorization layer. Do not expose it publicly without adding access control, rate limiting, request-size limits, and an appropriate network boundary.
- Video downloads and Azure processing can be long-running. Use a background-job pattern for production workloads rather than relying on a single synchronous HTTP request.
- Validate model findings with a qualified reviewer. Retrieval and LLM results can be incomplete or incorrect, especially when the knowledge base lacks a relevant rule.
- Establish retention, deletion, and access-control policies for videos, transcripts, OCR text, and audit reports before handling production content.

## License

No license file is currently included in this repository. Add an explicit license before distributing or reusing the project outside its intended scope.
