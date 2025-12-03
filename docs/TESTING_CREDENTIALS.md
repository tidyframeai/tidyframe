# TidyFrame Testing Credentials & Access Information

## 🔐 Site Password Protection

**Site Password Protection**: ✅ ENABLED  
**Site Password**: `xR5xODIMfZEF`

### Access URLs
- **Frontend (Docker)**: http://localhost:3001/
- **Frontend (Dev Server)**: http://localhost:3000/
- **Backend API**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs

## 👥 Test User Accounts

### Admin Account
- **Email**: `admin@test.com`
- **Password**: `admin123`
- **Full Name**: Test Admin
- **Plan**: Enterprise
- **Permissions**: ✅ Admin Access
- **Monthly Limit**: 1,000,000 parses
- **Status**: Active & Verified

### Regular User Account  
- **Email**: `user@test.com`
- **Password**: `user123`
- **Full Name**: Test User
- **Plan**: Standard
- **Permissions**: Regular User
- **Monthly Limit**: 100,000 parses
- **Status**: Active & Verified

## 🚀 Testing Flow

### 1. Site Access
1. Navigate to http://localhost:3001/
2. You will see the site password gate
3. Enter password: `xR5xODIMfZEF`
4. Click "Access Site"

### 2. User Authentication
After passing the site password gate:
1. Click "Login" 
2. Use either test account credentials
3. Admin account has access to admin features
4. Regular user account has standard access

### 3. Admin vs User Testing
- **Admin Account**: Can access all features, admin panel, unlimited processing
- **User Account**: Standard features, 100K monthly limit, no admin access

## 🔧 Environment Configuration

### Files Updated
- `./.env` - Development environment
- `./backend/.env` - Backend environment
- `./.env.production` - Production environment

### Key Changes Made
- `ENABLE_SITE_PASSWORD=true` in all environment files
- `SITE_PASSWORD=xR5xODIMfZEF` (consistent across all environments)
- Test accounts created with proper permissions and plans

## 📋 Account Verification

Both test accounts have been verified with:
- ✅ Proper password hashing
- ✅ Email verification status set to true
- ✅ Active status enabled
- ✅ Correct plan assignments (Enterprise/Standard)
- ✅ Admin flag set correctly
- ✅ Monthly limits configured
- ✅ Zero failed login attempts

## 🛠 Maintenance

### Re-creating Test Accounts
If you need to recreate the test accounts:
```bash
docker exec tidyframe-backend-1 python3 /path/to/create_test_accounts.py
```

### Disabling Site Password
To disable site password protection, set in environment files:
```bash
ENABLE_SITE_PASSWORD=false
```

### Changing Site Password
Update the `SITE_PASSWORD` value in all environment files and restart services:
```bash
docker restart tidyframe-backend-1 tidyframe-frontend-1
```

## 📝 Notes

- All passwords are stored securely using bcrypt hashing
- Test accounts are marked as verified to skip email verification
- Admin account has unlimited parsing capability
- Site password protection applies to all routes except admin and auth pages
- Environment changes require service restart to take effect

## 🔒 Security

- Site password: `xR5xODIMfZEF` (production-grade)
- Admin password: `admin123` (development only - change for production)
- User password: `user123` (development only - change for production)
- All accounts use proper bcrypt password hashing
- Email verification is auto-enabled for test accounts

---

**Last Updated**: $(date)  
**Created**: September 11, 2025  
**Status**: ✅ Ready for Testing