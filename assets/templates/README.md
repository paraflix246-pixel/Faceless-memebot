# Custom meme templates

Drop background images here to use them as meme templates. They are auto-discovered at runtime.

## How it works

1. Add a PNG or JPG file to this folder, e.g. `my_background.png`
2. Run `python -m memebot templates` — you'll see `custom_my_background` listed
3. Generate memes normally — custom templates are picked randomly alongside built-ins

## Example

```
assets/templates/
├── README.md          ← this file
└── gradient_bg.png    ← becomes template name: custom_gradient_bg
```

Custom templates overlay top/bottom caption bars on your image, scaled to 9:16 (1080×1920).

## Tips

- Use high-contrast areas at top and bottom for readable text
- Portrait-oriented images work best
- Keep filenames short and descriptive (no spaces if possible)
