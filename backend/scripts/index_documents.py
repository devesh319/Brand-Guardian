import os
import glob
import logging
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import AzureOpenAIEmbeddings
from langchain_azure_ai.vectorstores import AzureSearch

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("indexer")


def index_documents():
    """
    Reads the PDFs, chunks them and upload them to Azure AI Search
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, "../../backend/data")

    # Check Env Vars
    logger.info("=" * 60)
    logger.info("Environment COnfiguration Check:")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {os.getenv("AZURE_OPENAI_ENDPOINT")}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {os.getenv("AZURE_OPENAI_API_VERSION")}")
    logger.info(
        f"AZURE_OPENAI_EMBEDDING_DEPLOYMENT: {os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")}"
    )
    logger.info(f"AZURE_SEARCH_ENDPOINT: {os.getenv("AZURE_SEARCH_ENDPOINT")}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {os.getenv("AZURE_SEARCH_INDEX_NAME")}")

    # Validate Required variables
    required = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX_NAME",
    ]

    missing_vars = [var for var in required if not os.getenv(var)]

    if missing_vars:
        logging.error(f"Missing Environment Variables: {",".join(missing_vars)}")
        logging.error("Please check your .env file and ensure all variables are set")
        return

    # Initialize the Azure OpenAI Embeddings Model
    try:
        logger.info("Initializing the Azure OpenAI Embeddings Model")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        logger.info("Initialization of Azure OpenAI Embeddings Model Successful")
    except Exception as e:
        logger.error(f"Azure OpenAI Embeddings Model Initialization failed: {str(e)}")
        return

    # Initialize the Azure AI Vector Store
    try:
        logger.info("Initializing the Azure AI Search Vector Store")
        vector_store = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
            embedding_function=embeddings.embed_query,
        )
        logger.info("Initialization of Azure AI Search Vector Store Successful")
    except Exception as e:
        logger.error(f"Azure OpenAI Embeddings Model Initialization failed: {str(e)}")
        return

    # Find the PDF Files
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))
    if not pdf_files:
        logger.warning("No PDF Files found!")
    else:
        logger.info(
            f"Found {len(pdf_files)} files: {[os.path.basename(f) for f in pdf_files]} "
        )

    all_splits = []

    for pdf_path in pdf_files:
        try:
            base_name = os.path.basename(pdf_path)

            logger.info(f"Loading PDF {base_name}....")

            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            # Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            splits = text_splitter.split_documents(raw_docs)

            for split in splits:
                split.metadata["source"] = base_name

            all_splits.extend(splits)
            logger.info(f"Split the doc {base_name} into {len(splits)} chunks.")

        except Exception as e:
            logger.error(f"Failed Converting PDFs to vectors: {str(e)}")
            return

    # Upload to Azure
    if all_splits:
        logger.info(
            f"Uploading {len(all_splits)} chunks to Azure AI Index {os.getenv("AZURE_SEARCH_INDEX_NAME")}"
        )
        try:
            vector_store.add_documents(documents=all_splits)
            logger.info("=" * 60)
            logger.info("Indexing Complete! Knowledge Base is ready.")
            logger.info(f"Total Chunks indexed: {len(all_splits)}")
            logger.info("=" * 60)
        except Exception as e:
            logger.warning("Adding docs to vector store failed: {str(e)}")


if __name__ == "__main__":
    index_documents()
