# 🐑 IBU Dashboard - SheepIt Render Farm Team Analytics

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Render](https://img.shields.io/badge/Deploy-Render-purple.svg)](https://render.com)

> **A modern, cinematic web dashboard for tracking SheepIt Render Farm team performance and statistics.**

## 🎯 What is IBU?

**IBU (Intelligent Beings United)** is a collaborative team on [SheepIt Render Farm](https://www.sheepit-renderfarm.com/) - a distributed computing project that helps Blender artists render their 3D animations and images by sharing computational resources across a global network of volunteers.

### 🌍 About SheepIt Render Farm
- **Community-driven**: Free render farm powered by volunteers
- **Blender-focused**: Specializes in rendering Blender projects
- **Point-based system**: Contributors earn points for computational work
- **Global network**: Thousands of users worldwide sharing resources

### 👥 About Team IBU
Our team brings together passionate 3D artists, developers, and rendering enthusiasts who contribute their computational power to help the Blender community create amazing content.

## 🚀 What This Dashboard Does

The IBU Dashboard is a comprehensive analytics platform that provides:

### 📊 **Real-Time Team Analytics**
- **Live Statistics Panel**: Current team points, active members, and top performers
- **Interactive Pie Charts**: Visual breakdown of individual member contributions
- **Performance Tracking**: Historical data analysis and trends
- **Google Drive Integration**: Automatic data synchronization and updates

### 🎨 **Modern User Experience**
- **Cinematic Landing Page**: Animated particles and smooth transitions
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Interactive Visualizations**: Powered by Plotly for dynamic charts
- **Real-time Updates**: Live connection status and data refresh

### 🔧 **Technical Features**
- **Automated Data Collection**: Scrapes and processes team performance data
- **Cloud Integration**: Secure Google Drive API integration
- **Production Ready**: Environment variable configuration for secure deployment
- **Scalable Architecture**: Built with Flask for easy hosting and maintenance

## 🎭 Screenshots

### Landing Page
![Landing Page](static/IBU_SMILE_ICON.svg)
*Modern, animated landing page with live statistics panel*

### Team Analytics
*Interactive charts showing team member contributions and performance metrics*

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask 2.3+
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Data Visualization**: Plotly.js
- **Data Processing**: Pandas, NumPy
- **Cloud Services**: Google Drive API
- **Deployment**: Render.com compatible
- **Styling**: Modern CSS with animations and responsive design

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Google Service Account with Drive API access
- SheepIt team data access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ibu-dashboard.git
   cd ibu-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Drive credentials**
   ```bash
   # Set environment variable with your service account JSON
   export GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'
   
   # Or for development, place service_account.json in project root
   ```

4. **Run the application**
   ```bash
   python IBU_scraper.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:5000`

## 🌐 Deployment

### Deploy to Render

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on [Render](https://render.com)

3. **Set environment variables**:
   ```
   GOOGLE_SERVICE_ACCOUNT_KEY = (your service account JSON)
   FLASK_ENV = production
   ```

4. **Deploy** and enjoy your live dashboard!

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## 📋 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Google Service Account JSON credentials | Yes |
| `FLASK_ENV` | Flask environment (development/production) | No |
| `PORT` | Port number (auto-set by hosting platforms) | No |
| `DATA_FOLDER` | Local data storage folder | No |

### Google Drive Setup

1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create a Service Account
4. Download the JSON key file
5. Share your SheepIt data folder with the service account email

Detailed setup instructions available in [`DEPLOYMENT_SECURITY.md`](DEPLOYMENT_SECURITY.md)

## 🎯 Features & Goals

### ✅ **Current Features**
- Real-time team statistics display
- Interactive member contribution charts
- Automated data synchronization
- Responsive, modern UI
- Secure credential management
- Production-ready deployment

### 🚧 **Planned Features**
- Historical performance trends
- Member ranking system
- Export capabilities for reports
- Email notifications for milestones
- Advanced filtering and search
- Mobile app companion

### 🎨 **Design Philosophy**
- **User-Centric**: Intuitive interface that makes data accessible
- **Performance-Focused**: Fast loading and smooth interactions
- **Secure by Default**: Best practices for credential management
- **Community-Driven**: Built by and for the SheepIt community

## 🤝 Contributing

We welcome contributions from the community! Whether you're a developer, designer, or SheepIt enthusiast:

### Ways to Contribute
- 🐛 **Bug Reports**: Found an issue? Let us know!
- 💡 **Feature Requests**: Have ideas for improvements?
- 🔧 **Code Contributions**: Submit pull requests
- 📖 **Documentation**: Help improve our guides
- 🎨 **Design**: UI/UX improvements and suggestions

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## 📊 SheepIt Integration

This dashboard specifically tracks:
- **Individual Points**: Each team member's contribution
- **Team Ranking**: Position relative to other SheepIt teams
- **Active Members**: Currently participating team members
- **Historical Data**: Performance trends over time
- **Milestone Tracking**: Team achievements and goals

## 🔒 Security & Privacy

- **No Personal Data**: Only public SheepIt statistics are collected
- **Secure Credentials**: Environment variable-based authentication
- **Open Source**: Transparent codebase for community review
- **GDPR Compliant**: Respects user privacy and data protection

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SheepIt Render Farm**: For providing the amazing platform that makes this possible
- **Blender Community**: For creating and supporting open-source 3D creation
- **Team IBU Members**: For their continuous contributions and feedback
- **Open Source Community**: For the tools and libraries that power this dashboard

## 📬 Contact & Support

- **Team**: IBU (Intelligent Beings United)
- **Creator**: Mindeformer
- **Assistant**: GitHub Copilot
- **Community**: I.B.U members

### Links
- [SheepIt Render Farm](https://www.sheepit-renderfarm.com/)
- [Blender](https://www.blender.org/)
- [Team IBU Page](https://www.sheepit-renderfarm.com/team/[team-id])

---

<div align="center">

**Built with ❤️ by the IBU Team**

*Empowering the Blender community through collaborative rendering*

[![SheepIt](https://img.shields.io/badge/SheepIt-Render%20Farm-orange.svg)](https://www.sheepit-renderfarm.com/)
[![Blender](https://img.shields.io/badge/Blender-Community-blue.svg)](https://www.blender.org/)

</div>
