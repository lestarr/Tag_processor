from pydantic import BaseModel, Field
from typing import List, Optional


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