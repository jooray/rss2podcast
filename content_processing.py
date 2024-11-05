import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from ollama_client import OllamaClient
import nltk
from nltk.tokenize import sent_tokenize
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def clean_and_convert_content(content, is_markdown):
    if not is_markdown:
        # Clean HTML and convert to Markdown
        clean_html = clean_html_content(content)
        markdown_content = convert_html_to_markdown(clean_html)
    else:
        markdown_content = content

    # Remove images and links
    markdown_content = remove_images_and_links(markdown_content)
    return markdown_content

def prepare_for_speech(markdown_content, config):
    # Optional LLM Processing
    if config['blog_to_speech_llm']['enabled']:
        markdown_content = process_with_llm(markdown_content, config)
    return markdown_content

def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(['script', 'style']):
        script.decompose()
    return str(soup)

def convert_html_to_markdown(html_content):
    return md(html_content, strip=['a', 'img', 'b', 'i'], heading_style="ATX", escape_asterisks=False,
              escape_underscores=False, escape_misc=False, bullets='*')

def remove_images_and_links(markdown_content):
    markdown_content = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_content)
    markdown_content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', markdown_content)
    return markdown_content

def process_with_llm(markdown_content, config):
    try:
        ollama_client = OllamaClient(config['blog_to_speech_llm']['model'], url=config['blog_to_speech_llm']['endpoint'])
        max_chunk_size = config['blog_to_speech_llm']['max_chunk_size']

        chunks = split_content(markdown_content, max_chunk_size)
        processed_chunks = []

        for chunk in chunks:
            prompt = f"{config['blog_to_speech_llm']['prompt']}\n\n{chunk}"
            print(f"{Fore.GREEN}Processing chunk with LLM:{Style.RESET_ALL} \"{chunk}\"")
            response = ollama_client.generate(prompt)
            print(f"{Fore.GREEN}Processed chunk:{Style.RESET_ALL} \"{response}\"")

            if response and isinstance(response, str):
                verified = verify_output(chunk, response, config)
                if verified:
                    processed_chunks.append(response)
                else:
                    processed_chunks.append(chunk)
            else:
                processed_chunks.append(chunk)

        if len(processed_chunks) == len(chunks):
            return '\n\n'.join(processed_chunks)

        print(f"{Fore.RED}LLM processing failed. Using original content.{Style.RESET_ALL}")
        return markdown_content
    except Exception as e:
        print(f"{Fore.RED}Error in LLM processing: {e}{Style.RESET_ALL}")
        return markdown_content

def split_content(content, max_chunk_size):
    sentences = sent_tokenize(content)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk += sentence + "\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + "\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def verify_output(input_text, output_text, config):
    max_length_difference = config['blog_to_speech_llm']['max_length_difference']
    verifier_config = config['llm_verifier']

    # Length check
    input_length = len(input_text)
    output_length = len(output_text)
    length_difference = abs(input_length - output_length) / input_length

    if length_difference > max_length_difference:
        print(f"{Fore.RED}Length difference ({length_difference:.2%}) exceeds maximum allowed ({max_length_difference:.2%}){Style.RESET_ALL}")
        return False

    # If LLM verifier is not enabled, return True after passing length check
    if not verifier_config['enabled']:
        return True

    ollama_client = OllamaClient(verifier_config['model'], url=verifier_config['endpoint'])

    prompt = f"{verifier_config['prompt']}\n\nInput: {input_text}\n\nOutput: {output_text}"

    response = ollama_client.generate(prompt)
    if response.strip() == verifier_config['expected_output']:
        print(f"{Fore.GREEN}LLM validated the output, yay!{Style.RESET_ALL}")
        return True

    print(f"{Fore.RED}LLM verification failed:{Style.RESET_ALL} {response.strip()}")
    return False
