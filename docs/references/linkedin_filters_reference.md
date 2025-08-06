# LinkedIn Query Filters Reference

## Complete LinkedIn Filter Examples

| Filter Type | Description | Example Original Query | Generated Modified Query | Use Case |
|-------------|-------------|----------------------|-------------------------|----------|
| **All Content** | Searches all LinkedIn content | `data scientist` | `data scientist site:linkedin.com` | General LinkedIn search across all content types |
| **Profiles** | Personal LinkedIn profiles only | `software engineer python` | `software engineer python site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/"` | Finding professionals, potential hires, networking |
| **Companies** | Company pages only | `tech startups` | `tech startups site:linkedin.com inurl:"/company/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/" -inurl:"/in/"` | Company research, competitor analysis |
| **Posts** | LinkedIn feed posts and updates | `artificial intelligence trends` | `artificial intelligence trends site:linkedin.com (inurl:"/feed/" OR inurl:"/posts/") -inurl:"/company/" -inurl:"/in/" -inurl:"/jobs/" -inurl:"/pulse/"` | Industry discussions, thought leadership |
| **Jobs** | Job postings only | `remote developer` | `remote developer site:linkedin.com inurl:"/jobs/view/" -inurl:"/company/" -inurl:"/in/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/"` | Job hunting, market analysis |
| **Articles** | LinkedIn articles and publications | `machine learning best practices` | `machine learning best practices site:linkedin.com inurl:"/pulse/" -inurl:"/company/" -inurl:"/in/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/jobs/"` | Educational content, industry insights |

## Real-World Search Scenarios

### 🎯 Professional Networking
| Original Query | LinkedIn Filter | Generated Query | Purpose |
|---------------|----------------|-----------------|---------|
| `marketing manager toronto` | **Profiles** | `marketing manager toronto site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/"` | Finding marketing professionals in Toronto |
| `UX designer portfolio` | **Profiles** | `UX designer portfolio site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/"` | Discovering UX designers with portfolios |

### 🏢 Company Research
| Original Query | LinkedIn Filter | Generated Query | Purpose |
|---------------|----------------|-----------------|---------|
| `fintech companies london` | **Companies** | `fintech companies london site:linkedin.com inurl:"/company/"` | Researching fintech companies in London |
| `sustainable energy startups` | **Companies** | `sustainable energy startups site:linkedin.com inurl:"/company/"` | Finding green energy companies |

### 💼 Job Market Analysis
| Original Query | LinkedIn Filter | Generated Query | Purpose |
|---------------|----------------|-----------------|---------|
| `senior python developer` | **Jobs** | `senior python developer site:linkedin.com inurl:"/jobs/view/"` | Finding Python developer positions |
| `product manager remote` | **Jobs** | `product manager remote site:linkedin.com inurl:"/jobs/view/"` | Remote product management roles |

### 📝 Industry Insights
| Original Query | LinkedIn Filter | Generated Query | Purpose |
|---------------|----------------|-----------------|---------|
| `digital transformation 2024` | **Articles** | `digital transformation 2024 site:linkedin.com inurl:"/pulse/"` | Reading expert insights on digital transformation |
| `leadership skills development` | **Articles** | `leadership skills development site:linkedin.com inurl:"/pulse/"` | Educational content on leadership |

### 💬 Professional Discussions
| Original Query | LinkedIn Filter | Generated Query | Purpose |
|---------------|----------------|-----------------|---------|
| `cryptocurrency regulation` | **Posts** | `cryptocurrency regulation site:linkedin.com (inurl:"/feed/" OR inurl:"/posts/")` | Following industry discussions |
| `work from home productivity` | **Posts** | `work from home productivity site:linkedin.com (inurl:"/feed/" OR inurl:"/posts/")` | Professional opinions and tips |

## Advanced Search Patterns

### Multi-Keyword Combinations
```
Original: "senior software engineer javascript react"
LinkedIn Profiles: senior software engineer javascript react site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/"
LinkedIn Jobs: senior software engineer javascript react site:linkedin.com inurl:"/jobs/view/"
```

### Location-Specific Searches
```
Original: "data analyst san francisco"
LinkedIn Profiles: data analyst san francisco site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/"
LinkedIn Companies: data analyst san francisco site:linkedin.com inurl:"/company/"
```

### Industry-Specific Searches
```
Original: "healthcare technology innovation"
LinkedIn Articles: healthcare technology innovation site:linkedin.com inurl:"/pulse/"
LinkedIn Posts: healthcare technology innovation site:linkedin.com (inurl:"/feed/" OR inurl:"/posts/")
```

## Query Modifier Breakdown

### Profile Filter Exclusions
- `-inurl:"/company/"` - Excludes company pages
- `-inurl:"/jobs/"` - Excludes job listings
- `inurl:"/in/"` - Only includes personal profiles

### Content Type Targeting
- `inurl:"/company/"` - Targets company pages specifically
- `inurl:"/jobs/view/"` - Targets active job postings
- `inurl:"/pulse/"` - Targets published articles
- `(inurl:"/feed/" OR inurl:"/posts/")` - Targets social posts and updates

## Direct Google Search URLs

All generated queries can be tested directly by copying the URL from the Query Preview section in the Streamlit app. Example format:
```
https://www.google.com/search?q=software+engineer+site:linkedin.com+inurl:"/in/"+-inurl:"/company/"+-inurl:"/jobs/"
```

## Tips for Best Results

1. **Use Specific Keywords**: More specific queries yield better targeted results
2. **Combine Job Titles + Skills**: "python developer machine learning" works better than just "developer"
3. **Add Location**: Include city/country for geographically relevant results
4. **Industry Terms**: Use industry-specific terminology for professional searches
5. **Company Names**: Search for "{company name} employees" using Profile filter