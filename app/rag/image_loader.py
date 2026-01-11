# app/rag/image_loader.py
import base64
# import mimetypes

# mime_type, _ = mimetypes.guess_type(image_path)
# url = f"data:{mime_type};base64,{image_base64}"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def image_to_text(image_path, client):
    image_base64 = encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image clearly for knowledge retrieval."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()


