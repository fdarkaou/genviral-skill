# Template Commands

Templates are reusable slideshow structures. Convert winning slideshows into templates for faster iteration.

## list-templates
```bash
genviral list-templates
genviral list-templates --search hooks --limit 20 --offset 0
genviral list-templates --json
```

## get-template
```bash
genviral get-template --id TEMPLATE_ID
```

## create-template
Create a template from a validated template config object.

```bash
# File input
genviral create-template \
  --name "My Template" \
  --description "Description" \
  --visibility private \
  --config-file template-config.json

# Inline JSON
genviral create-template \
  --name "My Template" \
  --visibility workspace \
  --config-json '{"version":1,"structure":{"slides":[]},"content":{},"visuals":{}}'
```

Use exactly one of `--config-file` or `--config-json`. Config must match the template config v1 schema.

## update-template
```bash
genviral update-template --id TEMPLATE_ID --name "New Name"
genviral update-template --id TEMPLATE_ID --visibility workspace
genviral update-template --id TEMPLATE_ID --config-file new-config.json
genviral update-template --id TEMPLATE_ID --config-json '{"version":1,"structure":{"slides":[]},"content":{},"visuals":{}}'
genviral update-template --id TEMPLATE_ID --clear-description
```

Config input: use exactly one of `--config-file` or `--config-json` (not both).

## delete-template
```bash
genviral delete-template --id TEMPLATE_ID
```

## create-template-from-slideshow
Convert an existing slideshow into a reusable template.

```bash
genviral create-template-from-slideshow \
  --slideshow-id SLIDESHOW_ID \
  --name "Winning Format" \
  --description "Built from high-performing slideshow" \
  --visibility workspace \
  --preserve-text
```

`--preserve-text` supports both forms: `--preserve-text` (true) or `--preserve-text true|false`.
