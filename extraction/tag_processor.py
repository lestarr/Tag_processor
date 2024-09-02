import os
import json
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, ClassVar, Set
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field, validator
from openai import OpenAI
import instructor

# Assuming you have these imports and definitions from your original script
from extraction.models import TagsV, SynonymResult
from extraction.extract import extract_tags

# Initialize OpenAI client
client = instructor.patch(OpenAI())

# Set the cache directory path
CACHE_DIR = os.path.join('cache', 'new_products')
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize data structures
tag_frequency: Dict[str, int] = defaultdict(int)
product_titles: List[str] = []
synonym_maps: Dict[str, Dict[str, str]] = defaultdict(dict)
tag_to_books: Dict[str, Set[str]] = defaultdict(set)

def load_data():
    global tag_frequency, product_titles, synonym_maps, tag_to_books

    def load_json_file(filename):
        try:
            with open(os.path.join(CACHE_DIR, filename), 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"{filename} is empty. Starting with empty data structure.")
            return None

    # Check if product_titles.json exists and is not empty
    titles_data = load_json_file('product_titles.json')
    
    if titles_data is None or len(titles_data) == 0:
        print("No existing product titles found. Starting with fresh data structures.")
        tag_frequency = defaultdict(int)
        product_titles = []
        synonym_maps = defaultdict(dict)
        tag_to_books = defaultdict(set)
    else:
        print(f"Loading existing data. Found {len(titles_data)} product titles.")
        product_titles = titles_data

        # Load other data structures
        tag_books_data = load_json_file('tag_to_books.json')
        freq_data = load_json_file('tag_frequency.json')
        syn_data = load_json_file('synonym_maps.json')

        if tag_books_data is not None and freq_data is not None and syn_data is not None:
            tag_to_books = {k: set(v) for k, v in tag_books_data.items()}
            tag_frequency = defaultdict(int)
            for tag, freq in freq_data.items():
                if tag in tag_to_books:
                    tag_frequency[tag] = len(tag_to_books[tag])
                else:
                    print(f"Warning: Tag '{tag}' found in frequency data but not in tag_to_books. Skipping.")
            
            synonym_maps = defaultdict(dict)
            for tag_type, syn_map in syn_data.items():
                if isinstance(syn_map, dict):
                    synonym_maps[tag_type].update(syn_map)
                else:
                    print(f"Warning: synonym map for {tag_type} is not a dictionary. Skipping.")
        else:
            print("Some data files are missing or corrupted. Starting with fresh data structures.")
            tag_frequency = defaultdict(int)
            synonym_maps = defaultdict(dict)
            tag_to_books = defaultdict(set)

    print(f"Loaded {len(tag_frequency)} tags, {len(product_titles)} titles, {sum(len(syn_map) for syn_map in synonym_maps.values())} synonyms, and {len(tag_to_books)} tag-to-book mappings.")

def save_data():
    with open(os.path.join(CACHE_DIR, 'tag_frequency.json'), 'w') as f:
        json.dump(dict(tag_frequency), f)
    with open(os.path.join(CACHE_DIR, 'product_titles.json'), 'w') as f:
        json.dump(product_titles, f)
    with open(os.path.join(CACHE_DIR, 'synonym_maps.json'), 'w') as f:
        json.dump({k: dict(v) for k, v in synonym_maps.items()}, f)
    with open(os.path.join(CACHE_DIR, 'tag_to_books.json'), 'w') as f:
        json.dump({k: list(v) for k, v in tag_to_books.items()}, f)

def extract_title(text: str, doc_name: Optional[str] = None) -> str:
    lines = text.split('\n', 5)[:5]
    
    # Try to find a line starting with 'Title:'
    for line in lines:
        if 'Title:' in line:
            title = line.split('Title:', 1)[1].strip()
            print(f"Debug: Found title: {title}")
            return title
    
    # If no title found, use doc_name if provided
    if doc_name:
        return doc_name
    
    # If doc_name is None, use the first non-empty line with spaces replaced by underscores
    for line in lines:
        if line.strip():
            title = line.strip().replace(' ', '_')
            return title
    
    # If all else fails, return a default title
    return "Untitled_Document"

def process_product(description: str, doc_name: Optional[str] = None) -> Tuple[Optional[TagsV], Optional[Dict[str, int]]]:
    if(description == '' or len(description) < 100):
        print(f"\nWARNING: Document is TOO SHORT to process. SKIPPING document with text: {description[:100]}\n")
        return None, None
    title = extract_title(description, doc_name)
    print(f"Extracted title: {title}")
    if not title:
        print(f"No title found in the first 5 lines. Skipping this document.")
        return None, None
    
    if title in product_titles:
        print(f"Skipping document with title: {title}")
        return None, None
    
    try:
        tags, usage = extract_tags(description, TagsV)
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return None, None
    if tags.title is None:
        tags.title = title
    # Check title again after processing with TagsV model
    if tags.title in product_titles:
        print(f"Skipping document with title: {tags.title}")
        return None, None
    
    product_titles.append(tags.title)
    
    for tag_type, tag_value in tags.tag_types.items():
        if isinstance(tag_value, list):
            for tag in tag_value:
                update_tag_frequency(tag_type, tag, tags.title)
        elif tag_value:
            update_tag_frequency(tag_type, tag_value, tags.title)

    return tags, usage

def update_tag_frequency(tag_type: str, tag: str, book_title: str):
    if tag in tag_frequency:
        if book_title not in tag_to_books[tag]:
            tag_frequency[tag] += 1
            tag_to_books[tag].add(book_title)
    elif tag in synonym_maps[tag_type]:
        main_tag = synonym_maps[tag_type][tag]
        if book_title not in tag_to_books[main_tag]:
            tag_frequency[main_tag] += 1
            tag_to_books[main_tag].add(book_title)
    else:
        synonym = find_synonym(tag, list(tag_frequency.keys()), tag_type)
        if synonym:
            print(f"Synonym for {tag} found in {tag_type}: {synonym}")
            synonym_maps[tag_type][tag] = synonym
            if book_title not in tag_to_books[synonym]:
                tag_frequency[synonym] += 1
                tag_to_books[synonym].add(book_title)
        else:
            print(f"No synonym found for {tag} in {tag_type}. Adding as a new tag.")
            tag_frequency[tag] = 1
            tag_to_books[tag] = {book_title}


def find_synonym(new_tag: str, existing_tags: List[str], tag_type: str) -> Optional[str]:
    SynonymResult.existing_tags = existing_tags
    SynonymResult.tag_type = tag_type

    prompt = f"""Find a very close synonym for '{new_tag}' among these existing tags for {tag_type}: {', '.join(existing_tags)}. 
    Rules for finding synonyms:
    1. Only return a synonym if it has essentially the same meaning as the original tag.
    2. Do not return a synonym if it's a broader or narrower term, or if it's related but not equivalent.
    3. Never take a broader term for synonym.
    4. If no very close synonym exists, respond with None.
    5. You must choose from the provided list of existing tags or respond with None.

    Examples of good synonyms:
    - 'math' and 'mathematics'
    - 'programming' and 'coding'
    - 'machine learning' and 'ML'

    Examples of bad synonyms (do not do these):
    - 'calculus' and 'mathematics' (calculus is a subset of mathematics)
    - 'graphs' and 'mathematics' (graphs are a concept in mathematics, but not a synonym)
    - 'graphs' and 'visualization' (totally not synonyms)
    - 'python' and 'jupyter notebook' (related, but not synonyms)
    - 'neural networks' and 'programming' (neural networks involve programming, but are not synonymous)
    - 'Power BI' and 'data science' (data science is a broader term)

    Respond only with the synonym or None, without any additional text.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_model=SynonymResult,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that finds synonyms."},
                {"role": "user", "content": prompt}
            ],
            max_retries=2
        )
        
        return response.synonym if response.synonym != 'None' else None
    
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return None

def visualize_tag_frequency(freq_json_path: str):
    with open(freq_json_path, 'r') as f:
        tag_frequency = json.load(f)
    # Sort tags by frequency
    sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
    
    # Take top 30 tags
    top_tags = sorted_tags[:30]
    tags, frequencies = zip(*top_tags)
    
    # Create horizontal bar plot
    fig, ax = plt.subplots(figsize=(12, 10))
    y_pos = range(len(tags))
    ax.barh(y_pos, frequencies)
    
    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tags)
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel('Frequency')
    ax.set_title(f'Top {len(top_tags)} Tags by Frequency')
    
    # Add frequency labels at the end of each bar
    for i, v in enumerate(frequencies):
        ax.text(v, i, str(v), va='center')
    
    plt.tight_layout()
    plt.show()

    # Print information about books for each tag
    print("\nDetailed information for top 100 tags:")
    for tag, freq in top_tags[:100]:
        books = tag_to_books.get(tag, set())
        print(f"\nTag: {tag} (Frequency: {freq})")
        # Filter out None values and convert all items to strings
        valid_books = [str(book) for book in books if book is not None]
        print(f"Books: {', '.join(valid_books)}")

import re
def process_all_products(product_descriptions: List[str], doc_names: Optional[List[str]] = None):
    load_data()
    
    doc_names = check_length(product_descriptions, doc_names)
    
    for description, doc_name in zip(product_descriptions, doc_names):
        result = process_product(description, doc_name)
        if result:
            tags, usage = result
            if tags is None:
                print(f"Skipping: Unable to process tags for this description")
                continue
            
            tags_title = tags.title if hasattr(tags, 'title') and tags.title else 'Untitled'
            # clean title, remove all non-alphanumeric characters
            tags_title = tags_title.replace(' ', '_')
            tags_title = re.sub(r'[^A-Za-z0-9_]+', '', tags_title)
            print(f"Processed: {tags_title}")
            print(f"Usage: {usage}")
            print(f"tag_frequency: {tag_frequency}")
            print(f"tags: {tags}")
            
            # Create directories if they don't exist
            json_dir = os.path.join(CACHE_DIR, 'jsons')
            os.makedirs(json_dir, exist_ok=True)
            
            # save tags to file
            json_data = tags.model_dump_json(indent=4)
            json_path = os.path.join(json_dir, f'{tags_title}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
    
    save_data()
    return tag_frequency, tag_to_books, synonym_maps

def check_length(product_descriptions, doc_names):
    if doc_names is None:
        doc_names = [None] * len(product_descriptions)
    elif len(doc_names) < len(product_descriptions):
        # Extend doc_names with None values if it's shorter
        doc_names.extend([None] * (len(product_descriptions) - len(doc_names)))
    elif len(doc_names) > len(product_descriptions):
        # Truncate doc_names if it's longer
        doc_names = doc_names[:len(product_descriptions)]
    return doc_names



    

if __name__ == "__main__":
    texts = [open('data/product_description.txt', 'r').read()]
    process_all_products(texts)