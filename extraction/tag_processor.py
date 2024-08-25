import os
import json
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, ClassVar
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field, validator
from openai import OpenAI
import instructor

# Assuming you have these imports and definitions from your original script
from models import TagsV
from extract import extract_tags

# Initialize OpenAI client
client = instructor.patch(OpenAI())

# Set the cache directory path
CACHE_DIR = os.path.join( 'cache', 'math_books')
os.makedirs(CACHE_DIR, exist_ok=True)


# Initialize data structures
tag_frequency: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
product_titles: List[str] = []
synonym_maps: Dict[str, Dict[str, str]] = defaultdict(dict)

def load_data():
    global tag_frequency, product_titles, synonym_maps
    tag_frequency = defaultdict(lambda: defaultdict(int))
    product_titles = []
    synonym_maps = defaultdict(dict)

    def load_json_file(filename):
        try:
            with open(os.path.join(CACHE_DIR, filename), 'r') as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    return json.loads(content)
                else:
                    print(f"File {filename} is empty. Starting with empty data structure.")
                    return {}
        except json.JSONDecodeError:
            print(f"Error decoding {filename}. Starting with empty data structure.")
            return {}
        except FileNotFoundError:
            print(f"File {filename} not found. Starting with empty data structure.")
            return {}

    tag_frequency_data = load_json_file('tag_frequency.json')
    for tag_type, freq in tag_frequency_data.items():
        tag_frequency[tag_type].update(freq)

    product_titles_data = load_json_file('product_titles.json')
    if isinstance(product_titles_data, list):
        product_titles = product_titles_data
    else:
        print("product_titles.json does not contain a list. Starting with empty list.")

    synonym_maps_data = load_json_file('synonym_maps.json')
    for tag_type, syn_map in synonym_maps_data.items():
        synonym_maps[tag_type].update(syn_map)

    print(f"Loaded {sum(len(freq) for freq in tag_frequency.values())} tags, {len(product_titles)} titles, and {sum(len(syn_map) for syn_map in synonym_maps.values())} synonyms.")

def save_data():
    with open(os.path.join(CACHE_DIR, 'tag_frequency.json'), 'w') as f:
        json.dump({k: dict(v) for k, v in tag_frequency.items()}, f)
    with open(os.path.join(CACHE_DIR, 'product_titles.json'), 'w') as f:
        json.dump(product_titles, f)
    with open(os.path.join(CACHE_DIR, 'synonym_maps.json'), 'w') as f:
        json.dump({k: dict(v) for k, v in synonym_maps.items()}, f)

def extract_title(text: str) -> Optional[str]:
    lines = text.split('\n', 5)[:5]
    for line in lines:
        if line.startswith('Title:'):
            return line.split('Title:', 1)[1].strip()
    return None

def process_product(description: str) -> Tuple[Optional[TagsV], Optional[Dict[str, int]]]:
    title = extract_title(description)
    
    if not title:
        print(f"No title found in the first 5 lines. Skipping this document.")
        return None, None
    
    if title in product_titles:
        print(f"Skipping document with title: {title}")
        return None, None
    
    tags, usage = extract_tags(description, TagsV)
    
    # Check title again after processing with TagsV model
    if tags.title in product_titles:
        print(f"Skipping document with title: {tags.title}")
        return None, None
    
    product_titles.append(tags.title)
    
    for tag_type, tag_value in tags.tag_types.items():
        if isinstance(tag_value, list):
            for tag in tag_value:
                update_tag_frequency(tag_type, tag)
        elif tag_value:
            update_tag_frequency(tag_type, tag_value)

    return tags, usage

def update_tag_frequency(tag_type: str, tag: str):
    if tag in tag_frequency[tag_type]:
        tag_frequency[tag_type][tag] += 1
    elif tag in synonym_maps[tag_type]:
        main_tag = synonym_maps[tag_type][tag]
        tag_frequency[tag_type][main_tag] += 1
    else:
        if tag_frequency[tag_type]:
            synonym = find_synonym(tag, list(tag_frequency[tag_type].keys()), tag_type)
            if synonym:
                print(f"Synonym for {tag} found in {tag_type}: {synonym}")
                synonym_maps[tag_type][tag] = synonym
                tag_frequency[tag_type][synonym] += 1
            else:
                print(f"No synonym found for {tag} in {tag_type}. Adding as a new tag.")
                tag_frequency[tag_type][tag] = 1
        else:
            print(f"No existing tags for {tag_type}. Adding '{tag}' as a new tag.")
            tag_frequency[tag_type][tag] = 1

class SynonymResult(BaseModel):
    synonym: Optional[str] = Field(None, description="Word or phrase that has a very close meaning to the original tag and could be interchanged in the most contexts or None otherwise if no synonym exists")
    existing_tags: ClassVar[List[str]] = []
    tag_type: ClassVar[str] = ''

    @validator('synonym')
    def validate_synonym(cls, v):
        if v is not None and v != 'None' and v not in cls.existing_tags:
            raise ValueError(f"Synonym '{v}' is not in the list of existing tags for {cls.tag_type}: {cls.existing_tags}")
        return v

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
            model="gpt-4o-mini",
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

def visualize_tag_frequency():
    fig, axs = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Tag Frequency Distribution by Category')
    
    for (tag_type, freq), ax in zip(tag_frequency.items(), axs.flatten()):
        ax.bar(freq.keys(), freq.values())
        ax.set_title(tag_type)
        ax.set_xticklabels(freq.keys(), rotation=90)
        ax.set_ylabel('Frequency')
    
    plt.tight_layout()
    plt.show()

def process_all_products(product_descriptions: List[str]):
    global tag_frequency
    load_data()
    
    if not tag_frequency:
        print("Warning: tag_frequency is empty. Initializing with default values.")
        tag_frequency = defaultdict(int, {'mathematics': 1})  # Add a default tag if needed
    
    for description in product_descriptions:
        result = process_product(description)
        if result:
            tags, usage = result
            print(f"Processed: {tags.title if tags.title else 'Untitled'}")
            print(f"Usage: {usage}")
            visualize_tag_frequency()
    
    save_data()

if __name__ == "__main__":
    process_all_products(texts)