from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, ClassVar


class TagsV(BaseModel):
    """A collection of tags that can be used to describe a product, along with additional metadata."""
    
    title: Optional[str] = Field(
        None,
        description="Book title if available"
    )
    product_type: str = Field(
        ..., 
        description="Type of the product (e.g., eBook, course, template)"
    )
    target_audience: str = Field(
        ..., 
        description="Target audience for the product (e.g., beginner, intermediate, advanced)"
    )

    main_content_category: str = Field(
        ..., 
        description="Main category of the content (e.g., education, art, gaming)"
    )
    content_subcategory: Optional[str] = Field(
        None, 
        description="Subcategory within the main content category (e.g., digital_art, tabletop_gaming)"
    )
    age_group: Optional[str] = Field(
        None, 
        description="Age group targeted by the product only if the group is NOT adults (e.g., children, teenagers, 5th_grade)"
    )
    tags: List[str] = Field(
        ..., 
        description="A list of additional tags that can be used to describe a product."
    )

    @property
    def tag_types(self):
        return {
            'product_type': self.product_type,
            'target_audience': self.target_audience,
            'main_content_category': self.main_content_category,
            'content_subcategory': self.content_subcategory,
            'age_group': self.age_group,
            'tags': self.tags
        }
    
class SynonymResult(BaseModel):
    synonym: Optional[str] = Field(None, description="Word or phrase that has a very close meaning to the original tag and could be interchanged in the most contexts or None otherwise if no synonym exists")
    existing_tags: ClassVar[List[str]] = []
    tag_type: ClassVar[str] = ''

    @field_validator('synonym')
    @classmethod
    def validate_synonym(cls, v):
        if v is not None and v != 'None':
            if v not in cls.existing_tags:
                print(f"Warning: Synonym '{v}' is not in the list of existing tags for {cls.tag_type}: {cls.existing_tags}")
                return None
        return v
