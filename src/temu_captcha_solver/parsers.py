import logging
import re

LOGGER = logging.getLogger(__name__)

def get_list_of_objects_of_interest(challenge: str) -> list[str]:
    """Get the list of objects to select from Temu 3x3 captcha

    ex:
        input: 'Click on the corresponding images in the following order: 'television','strawberry','peach'
        output: ['television', 'strawberry', 'peach']
    """
    objects = re.findall(r"(?<=')[\w\s]+?(?=')", challenge)
    LOGGER.debug(f"input text: {challenge}\nobjects of interest: {str(objects)}") 
    return objects
