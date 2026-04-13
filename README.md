# BG Remover

A web-based tool that removes image backgrounds instantly using AI powered by rembg.

## Features

- **Instant Background Removal**: Upload images and remove backgrounds in seconds
- **Web Interface**: Simple drag-and-drop interface for easy use
- **API Access**: RESTful API for developers
- **Usage Tracking**: Monitor your API usage and limits
- **Multiple Plans**: Free and paid plans with different limits

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript, Tailwind CSS
- **AI Processing**: rembg (U²-Net model)
- **Database**: SQLite
- **File Handling**: Pillow

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bg-remover
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## API Documentation

### Remove Background

**Endpoint:** `POST /api/remove-bg`

**Headers:**
- `X-API-Key`: Your API key (required)
- `Content-Type`: multipart/form-data

**Body:**
- `file`: Image file (required)

**Response:**
- Success: Processed image file (PNG with transparent background)
- Error: JSON with error message

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/remove-bg \
  -H 'X-API-Key: your_api_key_here' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/image.jpg' \
  --output removed_bg.png
```

### Generate API Key

**Endpoint:** `POST /api/generate-key`

**Headers:**
- `Content-Type`: application/json

**Body:**
```json
{
  "email": "your@email.com",
  "plan": "free"  // Options: "free", "basic", "pro"
}
```

**Response:**
```json
{
  "api_key": "generated_api_key",
  "plan": "free",
  "max_usage": 5
}
```

### Check Usage

**Endpoint:** `GET /api/usage/{api_key}`

**Response:**
```json
{
  "usage_count": 2,
  "max_usage": 5,
  "remaining": 3,
  "plan": "free"
}
```

## Usage Limits

| Plan | Price | Images | Priority |
|------|-------|---------|----------|
| Free | ₹0 | 5 | Low |
| Basic | ₹49 | 50 | Medium |
| Pro | ₹99 | 150 | High |

## File Requirements

- **Supported Formats**: JPG, PNG, GIF, BMP, TIFF, WebP
- **Maximum Size**: 5MB
- **Output Format**: PNG with transparent background

## Project Structure

```
bg-remover/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── templates/
│   └── index.html        # Frontend HTML template
├── uploads/              # Temporary upload directory
├── outputs/              # Processed images directory
└── bg_remover.db         # SQLite database
```

## Deployment

### Using Gunicorn (Production)

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run the application:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Environment Variables

- `FLASK_ENV`: Set to `production` for production deployment
- `MAX_CONTENT_LENGTH`: Override default max file size (default: 5MB)

## Performance Notes

- Processing time: Typically 5-10 seconds per image
- Memory usage: Depends on image size and complexity
- CPU usage: High during processing (rembg is CPU-intensive)

## Security Considerations

- API keys are stored in database with usage tracking
- File uploads are validated for type and size
- Temporary files are cleaned up after processing
- CORS is configured for cross-origin requests

## Troubleshooting

### Common Issues

1. **"File size must be less than 5MB"**
   - Reduce image size before uploading
   - Compress the image using online tools

2. **"Invalid file type"**
   - Ensure file is one of the supported formats
   - Check file extension matches content type

3. **"Usage limit exceeded"**
   - Check your current usage via API
   - Upgrade to a paid plan if needed

4. **"Failed to process image"**
   - Check server logs for detailed error
   - Ensure rembg is properly installed

### Logs

Application logs are written to console. For production, consider configuring file logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review the API documentation

## Future Enhancements

- Bulk upload functionality
- Background color customization
- Mobile app development
- Faster AI model integration
- Passport photo maker
- Additional image editing features
