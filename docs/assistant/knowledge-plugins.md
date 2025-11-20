# Knowledge Base Plugins

Specialized knowledge collections as separate products (not tier-gated).

## Overview

Plugins are curated vector databases that extend the assistant's knowledge beyond general AI training. Available to all tiers as standalone products.

**Business Model**: Separate products ($5-$15 each) provide recurring revenue beyond SaaS subscriptions.

## Plugin Categories

### Free Core Plugins

Included with all tiers:

| Plugin | Documents | Description |
|--------|-----------|-------------|
| Basic Survival | ~50 | Water purification, shelter basics, fire starting |
| First Aid | ~30 | CPR, wound care, common injuries |
| Cooking | ~100 | Basic recipes, cooking techniques |

### Premium Knowledge Plugins

**Bunker-Buddy** ($15)
- **Documents**: 1,200+
- **Categories**: Survival, emergency preparedness, self-sufficiency
- **Content**:
  - Long-term water storage and purification
  - Food preservation (canning, dehydration, fermentation)
  - Shelter construction and fortification
  - Medical procedures for off-grid scenarios
  - Defense and security
  - Energy generation (solar, wind, manual)
  - Communication methods
  - Psychological resilience

**Medical Reference** ($10)
- **Documents**: 800+
- **Categories**: Healthcare, medications, procedures
- **Content**:
  - Drug interactions database
  - Symptom diagnosis trees
  - Emergency procedures
  - Dosage calculations
  - Contraindications
  - Alternative treatments

**Legal Assistant** ($10)
- **Documents**: 600+
- **Categories**: Contracts, corporate, personal
- **Content**:
  - Contract templates (NDA, employment, service agreements)
  - Legal concept explanations
  - State-specific requirements
  - Filing procedures
  - Legal term glossary

**Code Mentor** ($5)
- **Documents**: 400+
- **Categories**: Programming patterns, best practices
- **Content**:
  - Design patterns with examples
  - Language-specific idioms
  - Performance optimization
  - Security best practices
  - Code review checklist

### Integration Connectors

**Obsidian Connector** ($10)
- Index and search Obsidian vaults
- Bidirectional linking
- Tag and metadata extraction
- Daily notes integration
- Graph view queries

**Notion Connector** ($10)
- Sync Notion databases
- Query across workspaces
- Relation extraction
- Formula support
- Template access

**Google Drive Connector** ($10)
- Index cloud documents
- Real-time sync
- Shared folder support
- Version tracking
- OCR for scanned PDFs

## Plugin Architecture

### Manifest Format

```json
{
  "name": "bunker-buddy",
  "version": "1.2.0",
  "display_name": "Bunker-Buddy Survival Guide",
  "description": "Comprehensive survival and preparedness knowledge base",
  "author": "xSwarm Team",
  "license": "Proprietary",
  "price": 15.00,
  "categories": ["survival", "emergency", "preparedness"],
  "tags": ["water", "food", "shelter", "medical", "security"],
  "documents": 1247,
  "size_mb": 45,
  "last_updated": "2025-11-15",
  "auto_update": true,
  "min_version": "0.4.0",
  "dependencies": [],
  "icon": "bunker-buddy-icon.png"
}
```

### Directory Structure

```
plugins/bunker-buddy/
├── manifest.json           # Plugin metadata
├── icon.png               # 256x256 icon
├── README.md              # Plugin documentation
├── data/
│   ├── documents/         # Source documents
│   │   ├── water-storage.md
│   │   ├── food-preservation.md
│   │   └── ...
│   ├── embeddings.db      # Vector database
│   └── metadata.db        # Document metadata
└── updates/
    └── changelog.md       # Version history
```

### Vector Database Schema

Using SQLite with vector extension:

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT,
  content TEXT,
  embedding BLOB,  -- 1536-dim vector (ada-002)
  metadata JSON,
  created_at DATETIME,
  updated_at DATETIME
);

CREATE INDEX idx_category ON documents(category);
CREATE INDEX idx_embedding ON documents(embedding);  -- Vector index

CREATE VIRTUAL TABLE documents_fts USING fts5(
  title, content, category
);  -- Full-text search fallback
```

### Query Interface

```python
class KnowledgePlugin:
    def query(self, query: str, limit: int = 5, filters: dict = None):
        """
        Search plugin knowledge base.
        """
        # Embed query
        query_embedding = embed_text(query)

        # Vector similarity search
        results = self.db.execute("""
            SELECT id, title, content, category,
                   cosine_similarity(embedding, ?) as score
            FROM documents
            WHERE score > 0.7
            ORDER BY score DESC
            LIMIT ?
        """, (query_embedding, limit))

        return [
            {
                'id': r['id'],
                'title': r['title'],
                'content': r['content'],
                'category': r['category'],
                'score': r['score']
            }
            for r in results
        ]
```

## Integration Connector Details

### Obsidian Connector

**Features**:
- Watch vault for changes (inotify/fswatch)
- Parse markdown with frontmatter
- Extract wikilinks and tags
- Build graph relationships
- Index attachments (PDFs, images with OCR)

**Configuration**:
```toml
[plugins.obsidian]
vault_path = "~/Documents/ObsidianVault"
watch_changes = true
index_attachments = true
excluded_folders = ["templates", ".obsidian"]
```

**API**:
```python
# Query vault
results = query_knowledge(
    plugin='obsidian',
    query='project planning notes',
    filters={'tags': ['work', 'projects']}
)

# Create note
create_obsidian_note(
    title='Meeting Notes - 2025-11-19',
    content='...',
    tags=['meetings', 'work']
)
```

### Notion Connector

**Features**:
- OAuth authentication
- Sync databases and pages
- Query with Notion filters
- Relation traversal
- Formula evaluation

**Configuration**:
```toml
[plugins.notion]
api_token = "secret_..."
workspace_id = "..."
sync_interval = 3600  # 1 hour
databases = ["Tasks", "Projects", "Knowledge Base"]
```

**API**:
```python
# Query Notion database
results = query_knowledge(
    plugin='notion',
    query='Q4 objectives',
    filters={'database': 'Projects', 'status': 'Active'}
)

# Create Notion page
create_notion_page(
    database='Tasks',
    properties={
        'Name': 'Review documentation',
        'Status': 'In Progress',
        'Due Date': '2025-11-25'
    }
)
```

### Google Drive Connector

**Features**:
- OAuth authentication
- Index Google Docs, Sheets, PDFs
- Shared folder support
- Version tracking
- OCR for scanned documents
- Real-time change notifications (push API)

**Configuration**:
```toml
[plugins.google-drive]
client_id = "..."
client_secret = "..."
folders = ["Work", "Personal/Projects"]
file_types = ["document", "spreadsheet", "pdf"]
ocr_enabled = true
```

**API**:
```python
# Search Drive
results = query_knowledge(
    plugin='google-drive',
    query='Q3 financial report',
    filters={'folder': 'Work', 'type': 'spreadsheet'}
)
```

## Plugin Development

### Creating a Custom Plugin

**Step 1: Define Manifest**

```json
{
  "name": "my-knowledge-base",
  "version": "1.0.0",
  "display_name": "My Knowledge Base",
  "description": "Custom curated knowledge",
  "author": "Your Name",
  "license": "MIT",
  "categories": ["custom"],
  "price": 0.00
}
```

**Step 2: Prepare Documents**

```
my-knowledge-base/
└── data/
    └── documents/
        ├── topic1.md
        ├── topic2.md
        └── topic3.md
```

**Step 3: Generate Embeddings**

```bash
assistant plugins build my-knowledge-base
```

This will:
- Parse all documents
- Generate embeddings (OpenAI ada-002)
- Create vector database
- Build full-text search index

**Step 4: Test Plugin**

```bash
assistant plugins test my-knowledge-base "test query"
```

**Step 5: Package for Distribution**

```bash
assistant plugins package my-knowledge-base -o my-knowledge-base-v1.0.0.zip
```

### Plugin Development Guidelines

**Document Format**:
- Use Markdown for text content
- Include frontmatter metadata
- Keep documents focused (1-3 topics max)
- Use clear section headings
- Include examples where applicable

**Content Quality**:
- Verify factual accuracy
- Cite sources where possible
- Update regularly
- Test query relevance
- Optimize for common questions

**Performance**:
- Keep plugin size <100MB for fast downloads
- Limit document count (<2000 for responsiveness)
- Pre-generate embeddings (don't embed at query time)
- Use appropriate chunking for long documents

## Plugin Marketplace

### Listing Requirements

To list plugin in marketplace:

1. **Manifest** - Complete manifest.json
2. **Icon** - 256x256 PNG icon
3. **README** - Usage documentation
4. **License** - Clear license terms
5. **Pricing** - One-time or subscription
6. **Demo** - 3-5 example queries with expected results
7. **Changelog** - Version history

### Submission Process

```bash
# Test plugin locally
assistant plugins test my-plugin "sample query"

# Package for submission
assistant plugins package my-plugin

# Submit to marketplace
assistant plugins submit my-plugin-v1.0.0.zip \
  --category survival \
  --price 10.00 \
  --demo-queries demo.json
```

### Revenue Sharing

- **Platform Fee**: 30% on first year sales
- **Creator**: 70% on first year sales
- **Renewals**: Creator gets 85% (platform 15%)

### Quality Standards

Plugins must meet:
- Minimum 50 unique documents
- Average query relevance >0.7
- No copyright violations
- Regular updates (quarterly minimum for premium)
- Responsive support

## Installation & Updates

### User Installation

```bash
# Browse marketplace
assistant plugins search survival

# Install plugin
assistant plugins install bunker-buddy

# Verify installation
assistant plugins list
```

### Automatic Updates

```toml
[plugins.bunker-buddy]
auto_update = true
update_check_interval = 86400  # Daily
```

Update process:
1. Check for new version
2. Download delta if available
3. Verify checksum
4. Apply update atomically
5. Rebuild search index
6. Notify user

### Manual Updates

```bash
# Check for updates
assistant plugins check-updates

# Update specific plugin
assistant plugins update bunker-buddy

# Update all
assistant plugins update --all
```

## Usage Examples

### Query from Code

```python
# Import plugin system
from assistant.plugins import query_knowledge

# Query Bunker-Buddy
results = query_knowledge(
    plugin='bunker-buddy',
    query='How do I purify water without electricity?',
    limit=3
)

for result in results:
    print(f"Title: {result['title']}")
    print(f"Content: {result['content'][:200]}...")
    print(f"Score: {result['score']}\n")
```

### Query via Voice

```
User: "Hey assistant, check Bunker-Buddy for water storage methods"