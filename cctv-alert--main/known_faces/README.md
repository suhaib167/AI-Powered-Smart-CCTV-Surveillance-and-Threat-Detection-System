# Known Faces Database

Place reference images in this folder to enable face recognition.

## Guidelines

- Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`
- Filename becomes the person's display name (e.g. `john_doe.jpg` → "John Doe")
- Use clear, front-facing photos with good lighting
- One person per file recommended

## Example

```
known_faces/
├── alice_smith.jpg
├── bob_jones.png
└── security_guard.jpeg
```

Unknown persons (no match in this folder) will trigger security alerts.
