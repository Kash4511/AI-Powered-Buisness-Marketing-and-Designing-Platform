# Lead Magnet Generation System

This project is a high-quality lead magnet generator for architecture firms, powered by Django and Groq AI.

## Dynamic Theming Engine

The system supports dynamic theming based on user preferences or firm branding.

### API: `/api/theme/`

Returns the current theme palette.

- **URL:** `/api/theme/`
- **Method:** `GET`
- **Parameters:**
  - `mode` (optional): `light` or `dark`. Defaults to `light`.
- **Response:**
  ```json
  {
    "primary": "#1a365d",
    "secondary": "#c5a059",
    "surface": "#ffffff",
    "onSurface": "#1a202c",
    "accent": "#f8fafc",
    "highlight": "#e8f4f8"
  }
  ```

## Image Helper API

The `GroqClient` includes a centralized image-rendering helper for responsive and accessible layouts.

### `render_image(url, alt, aspect_ratio="16/9", lazy=True)`

- **Parameters:**
  - `url`: The URL of the image.
  - `alt`: Alternative text for accessibility.
  - `aspect_ratio`: Desired aspect ratio (e.g., "16/9", "4/3").
  - `lazy`: Whether to use lazy loading.
- **Returns:** A responsive `<picture>` element with CLS (Cumulative Layout Shift) prevention.
