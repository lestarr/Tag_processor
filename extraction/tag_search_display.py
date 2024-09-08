import json
import ipywidgets as widgets
from IPython.display import display, clear_output

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def main(tag_freq_json, tag_to_books_json):

    # Load the data
    tag_frequency = load_json(tag_freq_json)
    tag_to_books = load_json(tag_to_books_json)

    # Sort tags by frequency
    MIN_FREQUENCY = 1  # You can easily change this value
    sorted_tags = sorted([(tag, freq) for tag, freq in tag_frequency.items() if freq > MIN_FREQUENCY], key=lambda x: x[1], reverse=True)

    # Create widgets
    tag_checkboxes = [widgets.Checkbox(description=f"{tag} ({freq})", value=False, layout=widgets.Layout(width='300px')) for tag, freq in sorted_tags]
    output = widgets.Output()

    # Create a function to handle checkbox changes
    def on_checkbox_change(change):
        selected_tags = [cb.description.split(' (')[0] for cb in tag_checkboxes if cb.value]
        with output:
            clear_output()
            if not selected_tags:
                print("No tags selected. Please select one or more tags.")
            else:
                # Find books that have all selected tags
                common_books = set.intersection(*[set(tag_to_books.get(tag, [])) for tag in selected_tags])
                print(f"Books tagged with all of: {', '.join(selected_tags)}")
                if common_books:
                    for book_title in common_books:
                        print(f"- {book_title}")
                else:
                    print("No books found with all selected tags.")

    # Attach the function to each checkbox
    for checkbox in tag_checkboxes:
        checkbox.observe(on_checkbox_change, names='value')

    # Create a VBox to hold all the checkboxes
    checkboxes_box = widgets.VBox(tag_checkboxes)

    # Create a search box
    search_box = widgets.Text(
        value='',
        placeholder='Search tags...',
        description='Search:',
        disabled=False
    )

    # Function to filter checkboxes based on search
    def filter_checkboxes(change):
        search_term = change['new'].lower()
        for checkbox in tag_checkboxes:
            if search_term in checkbox.description.lower():
                checkbox.layout.display = None
            else:
                checkbox.layout.display = 'none'

    search_box.observe(filter_checkboxes, names='value')

    # Create a "Clear All" button
    clear_button = widgets.Button(description="Clear All")

    def clear_all(b):
        for checkbox in tag_checkboxes:
            checkbox.value = False

    clear_button.on_click(clear_all)

    # Layout
    left_side = widgets.VBox([search_box, clear_button, checkboxes_box])
    right_side = widgets.VBox([output])
    main_layout = widgets.HBox([left_side, right_side])

    # Display the widgets
    display(main_layout)

if __name__ == "__main__":
    tag_freq_json = 'cache/display_tags/tag_frequency.json'
    tag_to_books_json = 'cache/display_tags/tag_to_books.json'
    main(tag_freq_json, tag_to_books_json)