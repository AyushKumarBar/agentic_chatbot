from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


load_dotenv()
# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/health")
def health_check_new():
    """Health check endpoint for the API."""
    return {"status": "ok"}


llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=1000,
)


def is_garbled(text: str) -> bool:
    """Check if a given text contains a high proportion of non-ASCII characters.

    Args:
        text (str): The text to check for garbled content.

    Returns:
        bool: True if the text contains a high proportion of non-ASCII characters, False otherwise.
    """
    non_ascii_count = sum(1 for char in text if ord(char) > 127)
    return non_ascii_count > len(text) * 0.3


def scrape_website(url: str) -> Dict[str, str]:
    """Scrape content from the given URL and return structured data.

    Args:
        url (str): The URL to scrape content from.

    Returns:
        Dict[str, str]: A dictionary containing the source URL and the scraped content.
    """
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract text content
        texts = soup.stripped_strings
        content = " ".join(texts)

        # Check for garbled text
        if is_garbled(content):
            logger.warning(f"Garbled text detected for URL: {url}")
            return {"source": url, "content": ""}

        # Trim content and ensure sentence boundary
        trimmed_content = content[:2]
        last_sentence_end = trimmed_content.rfind(". ")
        if last_sentence_end != -1:
            content = trimmed_content[: last_sentence_end + 1]
        else:
            content = trimmed_content

        return {"source": url, "content": content}

    except requests.HTTPError as e:
        logger.error(f"HTTPError for URL {url}: {e}")
        return {"source": url, "content": ""}
    except requests.RequestException as e:
        logger.error(f"RequestException for URL {url}: {e}")
        return {"source": url, "content": ""}
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return {"source": url, "content": ""}


def add_content_to_results(results: List[Dict], link: str = "link"):
    """
    Add content to the results serially, stopping when valid content is found.
    Limits results from the same domain to avoid redundancy.

    Args:
        results (List[Dict]): List of search results to process
        link (str): Key name for the URL in result dictionaries

    Returns:
        List[Dict]: Processed results with content added
    """
    MAX_RESULTS = 5  # Maximum results to process
    MAX_PER_DOMAIN = 1  # Maximum results per domain
    VALID_CONTENT_LIMIT = 2  # Number of valid content pieces to collect before breaking

    results_to_process = results[:MAX_RESULTS]
    processed_results = []
    domain_count = {}
    valid_content_count = 0

    def extract_domain(url: str) -> str:
        """Extract the main domain from a URL."""
        try:
            # Remove protocol (http:// or https://) and get domain
            domain = url.split("//")[-1].split("/")[0]
            # Remove 'www.' if present
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return url

    for result in results_to_process:
        url = result.get(f"{link}", "")
        domain = extract_domain(url)

        # Skip if we've already processed maximum allowed results from this domain
        if domain_count.get(domain, 0) >= MAX_PER_DOMAIN:
            continue

        # Extract content from the result link
        content_data = scrape_website(url)

        # Add the content to the result
        result["content"] = content_data.get("content", "")

        # Only count this result if we got valid content
        if result["content"].strip():
            domain_count[domain] = domain_count.get(domain, 0) + 1
            processed_results.append(result)
            valid_content_count += 1

            # Break if we've found enough valid content
            if valid_content_count >= VALID_CONTENT_LIMIT:
                break

    return processed_results


def exract_search_results(results: List[Dict]) -> str:
    """Extract search results from the given list of dictionaries."""

    extracted_results = ""
    for item in results:
        for key, value in item.items():
            extracted_results += f"{key}: {value}\n"

    return extracted_results


def search_duckduckgo_text(query: str, region: str = "wt-wt") -> List:
    """
    Search DuckDuckGo for results based on the given query.

    Args:
        query (str): The search query for DuckDuckGo.
        region(str): [Optional] : region for which to make query

    Returns:
        List: A list containing the status and either the search result or an error message.
        [
            {
                "title": "News, sport, celebrities and gossip | The Sun",
                "href": "https://www.thesun.co.uk/",
                "body": "Get the latest news, exclusives, sport, celebrities, showbiz, politics, business and lifestyle from The Sun",
                "content": "Get the latest news, exclusives, sport, celebrities, showbiz, politics, business and lifestyle from The Sun",
            }, ...
        ]
    """

    try:
        # Initialize DDGS and perform text search
        num = 2
        ddgs = DDGS(timeout=3)
        results = ddgs.text(keywords=query, region=region, max_results=num)
        # Ensure the result is a list
        if isinstance(results, list):
            return add_content_to_results(results, "href")
        else:
            return []
    except Exception as e:
        logger.error(f"Error searching DuckDuckGo for query '{query}': {e}")
        return []


def search_duckduckgo_news(query: str, region: str = "wt-wt") -> list:
    """
    Search DuckDuckGo for results based on the given query.

    Args:
        query (str): The search query for DuckDuckGo.
        region(str): [Optional] : region for which to make query

    Returns:
        list: A list containing the search results or an empty list in case of an error or invalid output.
            [
                {
                    "date": "2024-07-03T16:25:22+00:00",
                    "title": "Murdoch's Sun Endorses Starmer's Labour Day Before UK Vote",
                    "body": "Rupert Murdoch's Sun newspaper endorsed Keir Starmer and his opposition Labour Party to win the UK general election, a dramatic move in the British media landscape that illustrates the country's shifting political sands.",
                    "url": "https://www.msn.com/en-us/money/other/murdoch-s-sun-endorses-starmer-s-labour-day-before-uk-vote/ar-BB1plQwl",
                    "image": "https://img-s-msn-com.akamaized.net/tenant/amp/entityid/BB1plZil.img?w=2000&h=1333&m=4&q=79",
                    "source": "Bloomberg on MSN.com",
                    "content": "Rupert Murdoch's Sun newspaper endorsed Keir Starmer and his opposition Labour Party to win the UK general election, a dramatic move in the British media landscape that illustrates the country's shifting political sands.",
                }, ...
            ]

    """
    try:
        # Initialize DDGS and perform news search
        num = 2
        ddgs = DDGS(timeout=3)
        results = ddgs.news(query, region, max_results=num)

        # Ensure the result is a list
        if isinstance(results, list):
            return add_content_to_results(results, "url")
        else:
            logger.error("DDG News search returned a non-list output.")
            return []
    except Exception as e:
        logger.error(f"Error Fetching from DDG:   {e}")
        return []


def search_duckduckgo_videos(query: str) -> list:
    """
    Search DuckDuckGo for results based on the given query.

    Args:
        query (str): The search query for DuckDuckGo.
        region(str): [Optional] : region for which to make query

    Returns:
        list: A list containing the search results or an empty list in case of an error or invalid output.
    """
    try:
        # Initialize DDGS and perform news search
        num = 5
        ddgs_results = DDGS().videos(f"youtube: {query}", max_results=num)
        formatted_videos = []

        for result in ddgs_results:
            if "youtube.com" in result.get("content", ""):
                formatted_videos.append(
                    {
                        "id": result["content"].split("v=")[-1],
                        "thumbnails": [result["images"]["medium"]],
                        "title": result["title"],
                        "description": result.get("description"),
                        "channel": result.get("statistics", {}).get(
                            "uploader", "YouTube"
                        ),
                        "publish_time": result.get("published"),
                        "link": result["content"],
                        "source": result["publisher"],
                    }
                )

        if isinstance(formatted_videos, list):
            return formatted_videos
        else:
            logger.error("DDG Video search returned a non-list output.")
            return []
    except Exception as e:
        logger.error(f"Error Fetching from DDG:   {e}")
        return []


def generate_response(message: str, search_results: Dict) -> str:
    """Function to generating response."""
    video_search_results = ""
    news_search_results = ""
    web_search_results = ""

    if search_results:
        video_search_results = exract_search_results(search_results.get("videos", []))
        news_search_results = exract_search_results(search_results.get("news", []))
        web_search_results = exract_search_results(search_results.get("web", []))

    prompt = """
    <|begin_of_text|>  
    <|start_header_id|>system<|end_header_id|>  
    You are an helpful assistant Peter. Your role is to answer questions and provide information to the user.
    And help them acheive their goals.
    <|eot_id|>
    
    <|start_header_id|>search_results<|end_header_id|>
    Video  Search Results :
    {video_search_results}
    
    News Search Results :
    {news_search_results}
    
    Web Search Results :
    {web_search_results}
    <|eot_id|>
    
    <|start_header_id|>user<|end_header_id|>
    Question : {input}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    template = PromptTemplate(
        template=prompt,
        input_variables=[
            "input",
            "video_search_results",
            "news_search_results",
            "web_search_results",
        ],
    )

    template = template.partial(video_search_results=video_search_results)
    template = template.partial(web_search_results=web_search_results)
    template = template.partial(news_search_results=news_search_results)

    chain = template | llm | StrOutputParser()

    response = chain.invoke(message)

    return response.strip()
    # return video_search_results

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_id = data.get("user_id")
            session_id = data.get("session_id")
            user_message = data.get("user_message", "")
            search = data.get("search", False)

            await websocket.send_json(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "chain_of_thought": False,
                    "chain_of_thought_message": "Looking at your message",
                    "message": "",
                    "search_results": {},
                }
            )
            if search:
                await websocket.send_json(
                    {
                        user_id: user_id,
                        "session_id": session_id,
                        "chain_of_thought": False,
                        "chain_of_thought_message": "Searching for external information",
                        "message": "",
                        "search_results": {},
                    }
                )

                web_search_results = search_duckduckgo_text(user_message)
                video_search_results = search_duckduckgo_videos(user_message)
                news_search_results = search_duckduckgo_news(user_message)

                search_results = {
                    "web": web_search_results,
                    "news": news_search_results,
                    "videos": video_search_results,
                }

                await websocket.send_json(
                    {
                        user_id: user_id,
                        "session_id": session_id,
                        "chain_of_thought": False,
                        "chain_of_thought_message": "Personalizing response",
                        "message": "",
                        "search_results": search_results,
                    }
                )

            else:
                search_results = {}
                await websocket.send_json(
                    {
                        user_id: user_id,
                        "session_id": session_id,
                        "chain_of_thought": False,
                        "chain_of_thought_message": "Personalizing response",
                        "message": "",
                        "search_results": search_results,
                    }
                )

            generated_message = generate_response(user_message, search_results)

            await websocket.send_json(
                {
                    user_id: user_id,
                    "session_id": session_id,
                    "chain_of_thought": True,
                    "chain_of_thought_message": "",
                    "message": generated_message,
                    "search_results": search_results,
                }
            )
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)