# CKAN Data Requests Extension

A CKAN extension that allows users to submit data requests and administrators to manage them through a web interface.

## 🚀 Features

- ✅ **User-friendly interface** for submitting data requests
- ✅ **Organization-based filtering** and categorization
- ✅ **Admin panel** for managing requests (approve, reject, respond)
- ✅ **Status tracking** (pending, completed, rejected)
- ✅ **Automatic database setup** with proper permissions
- ✅ **Responsive design** that fits CKAN's theme
- ✅ **Performance optimized** with database indexes

## 📋 Requirements

- CKAN 2.8+
- PostgreSQL
- Python 3.7+

## 🛠️ Installation

### Step 1: Clone the Extension

Navigate to your CKAN extensions directory and clone the repository:

```bash
# For Docker environments (typical path)
cd /srv/app/src

# For source installations
cd /usr/lib/ckan/default/src

# Clone the extension
git clone https://github.com/SeemsOdd/ckanext-data-requests.git
```

### Step 2: Install the Extension

```bash
# Navigate to the extension directory
cd ckanext-data-requests

# Install the extension
pip install -e .
```

### Step 3: Create Database Table

#### For Docker Environments:

```bash
# Access your database container (replace 'your-db-container-name' with your actual container name)
docker exec -it your-db-container-name bash

# Connect to the datastore database
psql -U postgres -d datastore
```

#### For Source Installations:

```bash
# Connect directly to PostgreSQL
sudo -u postgres psql -d datastore
```

#### Run the following SQL commands:

**⚠️ IMPORTANT:** Replace `X` and `Y` in the GRANT commands with your actual database users from your `.env` file:
- `X` = Your write user (e.g., `ckandbuser`, `ckan_default`)
- `Y` = Your read-only user (e.g., `datastore_ro`)

```sql
-- Create the main table
CREATE TABLE data_requests (
    _id SERIAL PRIMARY KEY,
    id INTEGER,
    user_id TEXT,
    username TEXT,
    title TEXT,
    organization_id TEXT,
    organization_name VARCHAR(200),
    request_date TIMESTAMP WITHOUT TIME ZONE,
    request_text TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'pending',
    admin_response TEXT,
    response_date TIMESTAMP WITHOUT TIME ZONE,
    responded_by TEXT
);

-- Grant permissions (REPLACE X and Y with your actual users!)
GRANT ALL PRIVILEGES ON TABLE data_requests TO X;
GRANT ALL PRIVILEGES ON SEQUENCE data_requests__id_seq TO X;
GRANT SELECT ON TABLE data_requests TO Y;

-- Create indexes for better performance
CREATE INDEX idx_data_requests_active ON data_requests(is_active);
CREATE INDEX idx_data_requests_status ON data_requests(status);
CREATE INDEX idx_data_requests_org ON data_requests(organization_id);
CREATE INDEX idx_data_requests_user ON data_requests(user_id);
CREATE INDEX idx_data_requests_date ON data_requests(request_date);
```

Exit PostgreSQL:
```sql
\q
```

### Step 4: Update CKAN Configuration

Edit your CKAN configuration file:

#### For Docker:
```bash
# Typical Docker path
nano /srv/app/ckan.ini
```

#### For Source Installation:
```bash
# Typical source installation path
nano /etc/ckan/default/ckan.ini
```

Add `data_requests` to the plugins list:
```ini
ckan.plugins = datastore datapusher ... data_requests
```

### Step 5: Restart CKAN

#### For Docker:
```bash
# From your project directory
docker compose restart
```

#### For Source Installation:
```bash
sudo systemctl restart ckan
# or
sudo service ckan restart
```

## 🎯 Usage

After installation, you can access:

- **Main page**: `http://your-ckan-site.com/data-requests`
- **Create request**: `http://your-ckan-site.com/data-requests/create`
- **Admin panel**: `http://your-ckan-site.com/data-requests/admin` (sysadmin only)

## 🔧 Configuration

### Database User Examples

Common `.env` file configurations:

```env
# Example 1: Standard Docker setup
CKAN_DB_USER=ckandbuser          # Use this for X
DATASTORE_READONLY_USER=datastore_ro  # Use this for Y

# Example 2: Alternative setup
CKAN_DB_USER=ckan_default        # Use this for X
DATASTORE_READONLY_USER=datastore_ro  # Use this for Y
```

### Finding Your Database Users

Check your `.env` file or CKAN configuration:

```bash
# Check .env file
cat .env | grep -i user

# Check CKAN config
grep -E "(datastore|sqlalchemy)" /path/to/your/ckan.ini
```

## 🐛 Troubleshooting

### Plugin Not Loading
```bash
# Check if plugin is in the list
grep "ckan.plugins" /path/to/your/ckan.ini

# Check Python import
python -c "import ckanext.data_requests.plugin; print('OK')"
```

### Database Connection Issues
```bash
# Test database connection
psql -U your_user -d datastore -h your_host

# Check permissions
psql -U your_user -d datastore -c "SELECT * FROM data_requests LIMIT 1;"
```

### Docker Container Names
```bash
# List running containers
docker ps

# Common database container names:
# - db
# - postgres
# - ckan-db-1
# - your-project-name_db_1
```

## 📝 License

This project is licensed under the AGPL-3.0 License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

If you encounter any issues:

1. Check the [troubleshooting section](#-troubleshooting)
2. Review CKAN logs: `docker logs your-ckan-container`
3. Open an issue on GitHub

---
