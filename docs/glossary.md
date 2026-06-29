# PlusPoint EDU - Comprehensive Domain Glossary

## 1. Domain-Specific Terms and Definitions

### A

**Agent Code** (Referral Code)
A unique code assigned to brokers/agents that allows students to register using their referral link. Validated against the `code-database` table during registration.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 48-59)
- Reference: `AccountController::addReferralCode()` in `app/Http/Controllers/AccountController.php` (line 481-492)

**Application Tracking**
A feature that allows students to track their application status through a dedicated portal for international university admissions.
- Reference: `README.md` (line 31)

**Abroad Education**
International higher education pursued in countries such as UK, Germany, Romania, Canada, Australia, New Zealand, Singapore, Malaysia, UAE, and India.
- Reference: `README.md` (line 14)

### B

**Broker**
A user role representing educational consultants or agents who guide students through the admissions process. Brokers can use agent codes to register students.
- Reference: `AccountController::authenticate()` in `app/Http/Controllers/AccountController.php` (line 115)
- Reference: `routes/web.php` (line 37)

**Blog Categories**
Organizational groupings for blog content stored in the `blog_categories` table, allowing categorization of educational articles.
- Reference: `blogsController::addCategory()` in `app/Http/Controllers/blogsController.php` (line 72-83)

**Blog Content**
Educational articles and resources published on the platform, stored in the `blogs` table with HTML-formatted content.
- Reference: `blogsController::uploadBlog()` in `app/Http/Controllers/blogsController.php` (line 85-145)

### C

**Citizenship**
A user's country of citizenship, stored as a profile attribute in the users table.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 179)
- Reference: `app/Exports/UsersExport.php` (line 21)

**Code Database**
A database table (`code-database`) that stores valid referral codes and their descriptions for broker registration validation.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 53)

**Contact Form**
A public-facing form for inquiries and feedback from prospective students and other visitors.
- Reference: `ContactFormController::submit()` in `app/Http/Controllers/ContactFormController.php` (line 10)

**Country Code**
International dialing code prefix for mobile phone numbers in contact forms.
- Reference: `ContactFormController::submit()` in `app/Http/Controllers/ContactFormController.php` (line 14)

### D

**Date of Birth (DOB)**
User's birth date, required to be at least 10 years before the current date for profile registration.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 177)

**Degree**
Academic degree type (Associate, Bachelor's, Master's, Professional, Doctorate, Vocational) conditionally stored based on education level.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 242-246)

**Designation**
Professional title or position held by a user, stored as a nullable field in the users table.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php` (line 19)

### E

**Education Level**
The current or target level of education (e.g., Associate Degree, Bachelor's Degree, Master's Degree, etc.).
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 227)

**Education Level Interest**
The preferred level of higher education a student is interested in pursuing.
- Reference: `AccountController::updateProfilePrefrences()` in `app/Http/Controllers/AccountController.php` (line 310)

**Education Country**
The country where a student completed or is completing their current education.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 228)

**English Proficiency**
Assessment of English language ability (IELTS, TOEFL, etc.), with conditional sub-scores for listening, writing, reading, and speaking.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 232)

**English Listening/Writing/Reading/Speaking**
Individual component scores for English language proficiency tests.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 251-259)

### G

**Graduation Status**
Current status of academic completion (graduated, currently studying, etc.).
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 229)

**Gender**
User's gender identity, required field in user profile.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 182)

### H

**Higher Education Country Preferences**
Three priority countries selected by students for pursuing higher education.
- Reference: `AccountController::updateProfilePrefrences()` in `app/Http/Controllers/AccountController.php` (line 305-307)

### I

**Institution**
The educational institution where a student completed or is completing their education.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 230)

### M

**Major**
The field of study or academic discipline pursued by a student.
- Reference: `AccountController::updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 262)

**Major Interest**
The preferred field of study for higher education.
- Reference: `AccountController::updateProfilePrefrences()` in `app/Http/Controllers/AccountController.php` (line 308)

**Mobile**
User's phone number, stored as a nullable field in the users table.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php` (line 21)

### P

**Passport**
User's passport number, required unique field for international student identification.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 180)

**Passport Expiry**
The expiration date of a user's passport.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 181)

**Profile Picture**
User's avatar image stored in the `profile_pic` directory with thumbnail generation.
- Reference: `AccountController::updateprofilePic()` in `app/Http/Controllers/AccountController.php` (line 369-401)

### R

**Referral Code**
See Agent Code.

**Residency**
User's country of residence.
- Reference: `AccountController::updateProfile()` in `app/Http/Controllers/AccountController.php` (line 183)

**Role**
User classification: admin, broker, or student. Determines access levels and dashboard views.
- Reference: `AccountController::authenticate()` in `app/Http/Controllers/AccountController.php` (line 115-127)

---

## 2. Technical Terms Unique to This Project

### A

**Admin Dashboard**
Administrative interface for managing users, referral codes, and blog content. Accessible only to users with 'admin' role.
- Reference: `AccountController::profileAdmin()` in `app/Http/Controllers/AccountController.php` (line 410)

**Admin Portal**
Dedicated section for administrators to manage referral codes and system configuration.
- Reference: `AccountController::adminPortalView()` in `app/Http/Controllers/AccountController.php` (line 424-431)

**Authenticate**
Laravel authentication method that validates user credentials against the users table.
- Reference: `AccountController::authenticate()` in `app/Http/Controllers/AccountController.php` (line 109)

### B

**Blade Template**
Laravel's templating engine used for rendering views with PHP syntax.
- Reference: `resources/views/` directory structure

**Blog Edit Portal**
Admin interface for uploading, managing, and deleting blog posts.
- Reference: `blogsController::blogsAdmin()` in `app/Http/Controllers/blogsController.php` (line 65-75)

### C

**Code-Database Table**
Custom database table storing referral codes and descriptions for broker validation.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 53)

### D

**Database Migration**
Laravel schema definition files that create and manage database table structures.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php`

### E

**Eloquent ORM**
Laravel's Object-Relational Mapping system for database interactions.
- Reference: `app/Models/User.php` (line 11)

**Email Verification**
Laravel's email verification feature for confirming user email addresses.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php` (line 17)

### F

**Flash Message**
Session-based temporary message displayed to users after form submission.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 73)

### G

**Guard**
Laravel authentication guard configuration defining how users are authenticated (session-based in this project).
- Reference: `config/auth.php` (line 33-37)

### H

**Hash**
Laravel's password hashing using bcrypt algorithm for secure password storage.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 70)

### I

**ImageManager**
Intervention Image library for image processing and thumbnail generation.
- Reference: `AccountController::updateprofilePic()` in `app/Http/Controllers/AccountController.php` (line 387-391)

### M

**Mailable**
Laravel class for defining email messages with templates.
- Reference: `app/Mail/ContactMail.php` (line 10)

**Middleware**
Laravel request/response filters that handle authentication and authorization.
- Reference: `routes/web.php` (line 31-32)

### P

**Password Reset Token**
Temporary token stored in `password_reset_tokens` table for password recovery.
- Reference: `AccountController::processForgotPassword()` in `app/Http/Controllers/AccountController.php` (line 506-514)

**PDF Parser**
Smalot PdfParser library for extracting text content from PDF documents.
- Reference: `blogsController::uploadBlog()` in `app/Http/Controllers/blogsController.php` (line 110-113)

**PhpWord**
PHPOffice library for converting DOCX documents to HTML content.
- Reference: `blogsController::uploadBlog()` in `app/Http/Controllers/blogsController.php` (line 104-109)

### R

**Remember Token**
Laravel token for "remember me" functionality in authentication.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php` (line 20)

### S

**Session**
Database-backed session storage for maintaining user state across requests.
- Reference: `config/session.php` (line 16)

**Session Table**
Database table (`sessions`) storing active user sessions.
- Reference: `database/migrations/0001_01_01_000000_create_users_table.php` (line 33-41)

### U

**UsersExport**
Excel export class for exporting user data with all profile attributes.
- Reference: `app/Exports/UsersExport.php` (line 1)

### V

**Validator**
Laravel's form validation class for validating request data.
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 34)

---

## 3. Abbreviations and Acronyms

| Abbreviation | Full Form | Context | Reference |
|---|---|---|---|
| **API** | Application Programming Interface | Web service endpoints for data exchange | `routes/web.php` |
| **BCRYPT** | Blowfish Cipher | Password hashing algorithm | `.env.example` (line 11) |
| **CSRF** | Cross-Site Request Forgery | Security protection mechanism | `config/session.php` (line 180) |
| **CSV** | Comma-Separated Values | Data export format | `app/Exports/UsersExport.php` |
| **DB** | Database | Laravel database facade | `AccountController.php` (line 16) |
| **DOB** | Date of Birth | User birth date field | `AccountController.php` (line 177) |
| **DOCX** | Office Open XML Document | Microsoft Word format | `blogsController.php` (line 100) |
| **ENV** | Environment | Configuration file for application settings | `.env.example` |
| **GD** | Graphics Draw | Image processing driver | `AccountController.php` (line 387) |
| **HTML** | HyperText Markup Language | Web page markup language | `blogsController.php` (line 104) |
| **HTTP** | HyperText Transfer Protocol | Web communication protocol | `config/session.php` (line 166) |
| **HTTPS** | HTTP Secure | Encrypted web communication | `config/session.php` (line 149) |
| **IELTS** | International English Language Testing System | English proficiency test | `AccountController.php` (line 232) |
| **JSON** | JavaScript Object Notation | Data format for API responses | `AccountController.php` (line 77) |
| **MAIL** | Mail Service | Email delivery system | `AccountController.php` (line 18) |
| **MVC** | Model-View-Controller | Architectural pattern | `bootstrap/app.php` |
| **MySQL** | My Structured Query Language | Relational database system | `config/database.php` (line 32) |
| **ORM** | Object-Relational Mapping | Database abstraction layer | `app/Models/User.php` |
| **PDF** | Portable Document Format | Document format | `blogsController.php` (line 110) |
| **PHP** | PHP: Hypertext Preprocessor | Server-side scripting language | `composer.json` (line 6) |
| **SMTP** | Simple Mail Transfer Protocol | Email transmission protocol | `config/mail.php` (line 36) |
| **SQL** | Structured Query Language | Database query language | `config/database.php` |
| **TOEFL** | Test of English as a Foreign Language | English proficiency test | `AccountController.php` (line 232) |
| **TLS** | Transport Layer Security | Encryption protocol | `config/mail.php` (line 41) |
| **URL** | Uniform Resource Locator | Web address | `config/app.php` (line 46) |
| **UTF-8** | Unicode Transformation Format | Character encoding standard | `config/database.php` (line 49) |
| **XLSX** | Office Open XML Spreadsheet | Excel format | `AccountController.php` (line 600) |

---

## 4. Entity Names and Their Business Meaning

### Database Tables

| Entity | Business Meaning | Reference |
|---|---|---|
| **users** | Core user entity storing student, broker, and admin profiles | `database/migrations/0001_01_01_000000_create_users_table.php` (line 13) |
| **password_reset_tokens** | Temporary tokens for password recovery functionality | `database/migrations/0001_01_01_000000_create_users_table.php` (line 26) |
| **sessions** | Active user session data for authentication state | `database/migrations/0001_01_01_000000_create_users_table.php` (line 33) |
| **code-database** | Referral codes for broker registration validation | `AccountController.php` (line 53) |
| **blog_categories** | Blog post categorization for content organization | `blogsController.php` (line 72) |
| **blogs** | Published blog posts with HTML content and metadata | `blogsController.php` (line 85) |
| **address** | User address information (model defined but not actively used) | `app/Models/Address.php` (line 10) |
| **migrations** | Laravel migration tracking table | `config/database.php` (line 166) |

### Eloquent Models

| Model | Purpose | Reference |
|---|---|---|
| **User** | Represents system users (students, brokers, admins) | `app/Models/User.php` |
| **Post** | Blog post model (defined but not actively used) | `app/Models/Post.php` |
| **Address** | User address model (defined but not actively used) | `app/Models/Address.php` |
| **AddressCategory** | Address categorization model (defined but not actively used) | `app/Models/AddressCategory.php` |

### Mail Classes

| Class | Purpose | Reference |
|---|---|---|
| **ContactMail** | Email notification for contact form submissions | `app/Mail/ContactMail.php` |
| **registration_mail** | Welcome email sent to newly registered users | `app/Mail/registration_mail.php` |
| **ResetPasswordEmail** | Password reset link email | `app/Mail/ResetPasswordEmail.php` |
| **passwordNotification** | Confirmation email after password change | `app/Mail/passwordNotification.php` |

### Controllers

| Controller | Business Function | Reference |
|---|---|---|
| **AccountController** | User registration, authentication, profile management, admin functions | `app/Http/Controllers/AccountController.php` |
| **blogsController** | Blog content management, categorization, upload/delete | `app/Http/Controllers/blogsController.php` |
| **ContactFormController** | Contact form submission and email notification | `app/Http/Controllers/ContactFormController.php` |
| **HomeController** | Home page rendering | `app/Http/Controllers/HomeController.php` |
| **AboutController** | About page rendering | `app/Http/Controllers/AboutController.php` |
| **StudentsController** | Students listing page | `app/Http/Controllers/StudentsController.php` |
| **EmailController** | Email sending utilities | `app/Http/Controllers/EmailController.php` |

---

## 5. API Terminology and Conventions

### Route Naming Conventions

Routes follow Laravel's dot-notation naming convention for organization:

| Route Name | HTTP Method | Purpose | Reference |
|---|---|---|---|
| **account.registration** | GET | Display registration form | `routes/web.php` (line 29) |
| **account.processRegistration** | POST | Process user registration | `routes/web.php` (line 30) |
| **account.login** | GET | Display login form | `routes/web.php` (line 31) |
| **account.authenticate** | POST | Authenticate user credentials | `routes/web.php` (line 32) |
| **account.profile** | GET | Display user profile | `routes/web.php` (line 38) |
| **account.profile.edu** | GET | Display education profile section | `routes/web.php` (line 39) |
| **account.profile.prefrences** | GET | Display education preferences section | `routes/web.php` (line 40) |
| **account.update-profile** | PUT | Update user profile information | `routes/web.php` (line 41) |
| **account.update-profile-edu** | PUT | Update education information | `routes/web.php` (line 42) |
| **account.update-profile-prefrences** | PUT | Update education preferences | `routes/web.php` (line 43) |
| **account.updateprofilepic** | POST | Update profile picture | `routes/web.php` (line 44) |
| **account.profile.admin** | GET | Display admin dashboard | `routes/web.php` (line 51) |
| **account.profile.admin.users** | GET | Display admin users management | `routes/web.php` (line 52) |
| **account.profile.admin.portal** | GET | Display admin portal | `routes/web.php` (line 53) |
| **admin.addReferralCode** | POST | Add new referral code | `routes/web.php` (line 57) |
| **admin.deleteReferralCode** | POST | Delete referral code | `routes/web.php` (line 58) |
| **export.users** | GET | Export users to Excel | `routes/web.php` (line 59) |
| **account.logout** | GET | Logout user | `routes/web.php` (line 61) |

### Response Format

**JSON Response Structure for Form Submissions:**
```json
{
  "status": boolean,
  "errors": object|array,
  "error": object|array
}
```
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 77-83)

### Request Validation Rules

**Password Validation Rules:**
- Minimum 8 characters
- At least one lowercase letter: `regex:/[a-z]/`
- At least one uppercase letter: `regex:/[A-Z]/`
- At least one digit: `regex:/[0-9]/`
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 40-44)

**Email Validation Rules:**
- Must be valid email format
- Must not contain uppercase letters: `regex:/^[^A-Z]/`
- Must be unique in users table
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 38)

**Agent Code Validation:**
- Optional field
- If provided, must exist in `code-database` table
- Reference: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 48-59)

### Middleware Groups

| Middleware | Purpose | Routes | Reference |
|---|---|---|---|
| **guest** | Allows only unauthenticated users | Registration, login, password reset | `routes/web.php` (line 31) |
| **auth** | Requires authenticated users | Profile, admin, logout | `routes/web.php` (line 36) |

---

## 6. Configuration and Environment Variable Names

### Application Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **APP_NAME** | Plus Point Education | Application display name | `.env.example` (line 1) |
| **APP_ENV** | local | Environment mode (local/production) | `.env.example` (line 2) |
| **APP_KEY** | (empty) | Application encryption key | `.env.example` (line 3) |
| **APP_DEBUG** | false | Debug mode toggle | `.env.example` (line 4) |
| **APP_TIMEZONE** | UTC | Application timezone | `.env.example` (line 5) |
| **APP_URL** | http://localhost | Application base URL | `.env.example` (line 6) |
| **APP_LOCALE** | en | Default application language | `.env.example` (line 8) |
| **APP_FALLBACK_LOCALE** | en | Fallback language | `.env.example` (line 9) |
| **APP_FAKER_LOCALE** | en_US | Faker library locale | `.env.example` (line 10) |
| **APP_MAINTENANCE_DRIVER** | file | Maintenance mode driver | `.env.example` (line 12) |

### Database Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **DB_CONNECTION** | mysql | Database driver (mysql/sqlite/pgsql/sqlsrv) | `.env.example` (line 16) |
| **DB_HOST** | 127.0.0.1 | Database server hostname | `.env.example` (line 17) |
| **DB_PORT** | 3306 | Database server port | `.env.example` (line 18) |
| **DB_DATABASE** | laravel | Database name | `.env.example` (line 19) |
| **DB_USERNAME** | root | Database user | `.env.example` (line 20) |
| **DB_PASSWORD** | (empty) | Database password | `.env.example` (line 21) |
| **DB_CHARSET** | utf8mb4 | Character encoding | `config/database.php` (line 49) |
| **DB_COLLATION** | utf8mb4_unicode_ci | Character collation | `config/database.php` (line 50) |

### Session Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **SESSION_DRIVER** | database | Session storage driver | `.env.example` (line 23) |
| **SESSION_LIFETIME** | 120 | Session timeout in minutes | `.env.example` (line 24) |
| **SESSION_ENCRYPT** | false | Encrypt session data | `.env.example` (line 25) |
| **SESSION_PATH** | / | Session cookie path | `.env.example` (line 26) |
| **SESSION_DOMAIN** | null | Session cookie domain | `.env.example` (line 27) |
| **SESSION_TABLE** | sessions | Session storage table | `config/session.php` (line 73) |
| **SESSION_EXPIRE_ON_CLOSE** | true | Expire session when browser closes | `config/session.php` (line 31) |
| **SESSION_HTTP_ONLY** | true | HTTP-only cookie flag | `config/session.php` (line 166) |
| **SESSION_SAME_SITE** | lax | SameSite cookie attribute | `config/session.php` (line 180) |

### Mail Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **MAIL_MAILER** | log | Mail driver (smtp/log/array/sendmail) | `.env.example` (line 31) |
| **MAIL_HOST** | 127.0.0.1 | SMTP server hostname | `.env.example` (line 32) |
| **MAIL_PORT** | 2525 | SMTP server port | `.env.example` (line 33) |
| **MAIL_USERNAME** | null | SMTP authentication username | `.env.example` (line 34) |
| **MAIL_PASSWORD** | null | SMTP authentication password | `.env.example` (line 35) |
| **MAIL_ENCRYPTION** | null | Encryption type (tls/ssl) | `.env.example` (line 36) |
| **MAIL_FROM_ADDRESS** | hello@example.com | Default sender email | `.env.example` (line 37) |
| **MAIL_FROM_NAME** | ${APP_NAME} | Default sender name | `.env.example` (line 38) |

### Cache Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **CACHE_STORE** | database | Cache driver | `.env.example` (line 43) |
| **CACHE_PREFIX** | (empty) | Cache key prefix | `.env.example` (line 44) |

### Queue Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **QUEUE_CONNECTION** | database | Queue driver | `.env.example` (line 41) |

### Broadcast Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **BROADCAST_CONNECTION** | log | Broadcasting driver | `.env.example` (line 40) |

### File System Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **FILESYSTEM_DISK** | local | Default filesystem disk | `.env.example` (line 42) |

### AWS Configuration (Optional)

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **AWS_ACCESS_KEY_ID** | (empty) | AWS access key | `.env.example` (line 46) |
| **AWS_SECRET_ACCESS_KEY** | (empty) | AWS secret key | `.env.example` (line 47) |
| **AWS_DEFAULT_REGION** | us-east-1 | AWS region | `.env.example` (line 48) |
| **AWS_BUCKET** | (empty) | AWS S3 bucket name | `.env.example` (line 49) |

### Vite Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **VITE_APP_NAME** | ${APP_NAME} | Frontend app name | `.env.example` (line 52) |

### Authentication Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **AUTH_GUARD** | web | Default authentication guard | `config/auth.php` (line 15) |
| **AUTH_PASSWORD_BROKER** | users | Password reset broker | `config/auth.php` (line 16) |
| **AUTH_MODEL** | App\Models\User | User model class | `config/auth.php` (line 57) |
| **AUTH_PASSWORD_RESET_TOKEN_TABLE** | password_reset_tokens | Password reset token table | `config/auth.php` (line 93) |
| **AUTH_PASSWORD_TIMEOUT** | 10800 | Password confirmation timeout (seconds) | `config/auth.php` (line 113) |

### Logging Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **LOG_CHANNEL** | stack | Default log channel | `.env.example` (line 14) |
| **LOG_STACK** | single | Log stack configuration | `.env.example` (line 15) |
| **LOG_LEVEL** | debug | Minimum log level | `.env.example` (line 17) |

### Security Configuration

| Variable | Default Value | Purpose | Reference |
|---|---|---|---|
| **BCRYPT_ROUNDS** | 12 | Bcrypt hashing rounds | `.env.example` (line 11) |

---

## 7. File and Directory Naming Conventions

### Controller Naming

Controllers follow the pattern `{Feature}Controller`:
- `AccountController` - User account operations
- `blogsController` - Blog management (note: lowercase 'b')
- `ContactFormController` - Contact form handling
- `HomeController` - Home page
- `AboutController` - About page
- `StudentsController` - Students listing
- `EmailController` - Email utilities

### Model Naming

Models use singular, PascalCase naming:
- `User` - User entity
- `Post` - Blog post entity
- `Address` - Address entity
- `AddressCategory` - Address category entity

### Mail Class Naming

Mail classes use descriptive names:
- `ContactMail` - Contact form notification
- `registration_mail` - Registration confirmation
- `ResetPasswordEmail` - Password reset email
- `passwordNotification` - Password change notification

### View Path Conventions

Views follow the pattern `resources/views/{section}/{feature}.blade.php`:
- `front.account.registration` - Registration form
- `front.account.login` - Login form
- `front.account.profiles.student_profile` - Student profile
- `front.account.profiles.admin_profile` - Admin dashboard
- `front.blog-posts.blogs` - Blog listing
- `mail.contactNotification` - Contact email template

### Database Table Naming

Tables use lowercase, snake_case naming:
- `users` - User records
- `password_reset_tokens` - Password reset tokens
- `sessions` - User sessions
- `code-database` - Referral codes (note: hyphenated)
- `blog_categories` - Blog categories
- `blogs` - Blog posts
- `address` - Address records

### Migration File Naming

Migrations follow Laravel's timestamp convention:
- `0001_01_01_000000_create_users_table.php` - Initial user table
- `0001_01_01_000001_create_cache_table.php` - Cache table
- `0001_01_01_000002_create_jobs_table.php` - Job queue table
- `2024_08_28_060204_create_posts_table.php` - Posts table

---

## 8. User Roles and Permissions

### Role Types

| Role | Access Level | Capabilities | Reference |
|---|---|---|---|
| **admin** | Full system access | Manage users, referral codes, blog content, view all data | `AccountController::authenticate()` (line 117) |
| **broker** | Agent access | Register students, view assigned student profiles | `AccountController::authenticate()` (line 121) |
| **student** | User access | Manage own profile, view educational resources | `AccountController::authenticate()` (line 125) |

### Admin-Specific Routes

- `/account/profile/admin` - Admin dashboard redirect
- `/account/profile/admin/users` - User management
- `/account/profile/admin/portal` - Referral code management
- `/account/profile/admin/blogs` - Blog management
- `/account/profile/admin/portal/add-referral-code` - Add referral code
- `/account/profile/admin/portal/delete-referral-code` - Delete referral code
- `/account/profile/admin/updloaded-files/export-users` - Export users to Excel

Reference: `routes/web.php` (line 51-59)

---

## 9. Data Validation Rules Summary

### User Registration Validation

| Field | Rules | Error Message | Reference |
|---|---|---|---|
| **name** | required | (default) | `AccountController::processRegistration()` (line 35) |
| **email** | required, email, regex:/^[^A-Z]/, unique | Email must not contain uppercase letters | `AccountController::processRegistration()` (line 36) |
| **password** | required, min:8, regex:/[a-z]/, regex:/[A-Z]/, regex:/[0-9]/ | Must contain lowercase, uppercase, digit | `AccountController::processRegistration()` (line 39-44) |
| **confirm_password** | required, same:password | Must match password | `AccountController::processRegistration()` (line 45) |
| **role** | required | (default) | `AccountController::processRegistration()` (line 46) |
| **agentCode** | nullable, custom validation | Invalid agent code | `AccountController::processRegistration()` (line 47-59) |

### Profile Update Validation

| Field | Rules | Reference |
|---|---|---|
| **name** | required, min:5 | `AccountController::updateProfile()` (line 175) |
| **email** | required, email, unique (excluding current user) | `AccountController::updateProfile()` (line 176) |
| **dob** | required, date, before_or_equal (10 years ago) | `AccountController::updateProfile()` (line 177) |
| **citizenship** | required | `AccountController::updateProfile()` (line 178) |
| **residency** | required | `AccountController::updateProfile()` (line 179) |
| **passportExpiry** | required | `AccountController::updateProfile()` (line 180) |
| **passport** | required, unique (excluding current user) | `AccountController::updateProfile()` (line 181) |
| **gender** | required | `AccountController::updateProfile()` (line 182) |

### Blog Upload Validation

| Field | Rules | Reference |
|---|---|---|
| **document** | required, mimes:docx,pdf, max:2048 | `blogsController::uploadBlog()` (line 97) |
| **title** | required | `blogsController::uploadBlog()` (line 98) |
| **category_id** | required | `blogsController::uploadBlog()` (line 99) |

### Contact Form Validation

| Field | Rules | Reference |
|---|---|---|
| **name** | required | `ContactFormController::submit()` (line 19) |
| **email** | required, email | `ContactFormController::submit()` (line 20) |
| **message** | required | `ContactFormController::submit()` (line 21) |
| **mobile** | required | `ContactFormController::submit()` (line 22) |

---

## 10. Key Features and Their Terminology

### Authentication System
- **Registration**: User account creation with role selection
- **Login**: Credential-based authentication
- **Password Reset**: Token-based password recovery
- **Session Management**: Database-backed session persistence
- **Email Verification**: Optional email confirmation (defined but not enforced)

### User Profile Management
- **Personal Information**: Name, email, mobile, designation
- **Identification**: Passport, citizenship, residency
- **Education Profile**: Education level, institution, graduation status, degree
- **Language Proficiency**: English test scores (IELTS/TOEFL) with component scores
- **Preferences**: Higher education country preferences, major interest, education level interest
- **Profile Picture**: Avatar with thumbnail generation

### Blog Management
- **Blog Categories**: Content organization
- **Blog Upload**: DOCX and PDF document conversion to HTML
- **Blog Display**: Paginated listing with category filtering
- **Blog Deletion**: Admin-only removal of blog posts

### Referral System
- **Agent Codes**: Unique codes for broker registration
- **Code Management**: Admin interface for adding/deleting codes
- **Code Validation**: Verification during student registration

### Data Export
- **User Export**: Excel export of all user data with comprehensive attributes
- **Export Format**: XLSX with headers

---

## 11. Security-Related Terminology

| Term | Definition | Reference |
|---|---|---|
| **Password Hashing** | Bcrypt algorithm with 12 rounds for secure password storage | `.env.example` (line 11) |
| **CSRF Protection** | Cross-Site Request Forgery prevention via session tokens | `config/session.php` |
| **Session Encryption** | Optional encryption of session data | `config/session.php` (line 43) |
| **HTTP-Only Cookies** | Cookies inaccessible to JavaScript for security | `config/session.php` (line 166) |
| **SameSite Cookies** | CSRF mitigation through cookie scope restriction | `config/session.php` (line 180) |
| **Email Verification** | Optional email confirmation for user accounts | `database/migrations/0001_01_01_000000_create_users_table.php` (line 17) |
| **Password Reset Token** | Time-limited token for password recovery | `database/migrations/0001_01_01_000000_create_users_table.php` (line 26) |
| **Authentication Guard** | Session-based authentication mechanism | `config/auth.php` (line 33) |

---

## 12. Integration and Third-Party Services

| Service | Purpose | Configuration | Reference |
|---|---|---|---|
| **Intervention Image** | Image processing and thumbnail generation | `composer.json` (line 8) | `AccountController::updateprofilePic()` |
| **Maatwebsite Excel** | Excel file generation and export | `composer.json` (line 11) | `AccountController::export()` |
| **PHPOffice PhpWord** | DOCX document parsing | `composer.json` (line 12) | `blogsController::uploadBlog()` |
| **Smalot PdfParser** | PDF document parsing | `composer.json` (line 13) | `blogsController::uploadBlog()` |
| **Laravel UI** | Authentication scaffolding | `composer.json` (line 10) | `routes/web.php` |
| **Laravel Tinker** | Interactive shell for debugging | `composer.json` (line 9) | Development tool |

---

## 13. Common Patterns and Conventions

### Validation Pattern
```php
$validator = Validator::make($request->all(), [
    'field' => 'rule1|rule2',
]);

if ($validator->passes()) {
    // Process valid data
} else {
    // Return errors
}
```
Reference: `AccountController::processRegistration()` (line 34-83)

### JSON Response Pattern
```php
return response()->json([
    'status' => boolean,
    'errors' => array,
]);
```
Reference: `AccountController::processRegistration()` (line 77-83)

### Flash Message Pattern
```php
session()->flash('success', 'Message text');
return redirect()->route('route.name');
```
Reference: `AccountController::processRegistration()` (line 73)

### Authentication Check Pattern
```php
if (Auth::check() && Auth::user()->role == 'admin') {
    // Admin-only logic
} else {
    return redirect()->route('account.login');
}
```
Reference: `AccountController::profileAdmin()` (line 410-416)

---

## 14. File Upload and Storage

### Profile Picture Storage
- **Directory**: `public/profile_pic/`
- **Thumbnail Directory**: `public/profile_pic/thumb/`
- **Formats**: JPEG, PNG, JPG, GIF, SVG
- **Max Size**: 2048 KB
- **Thumbnail Dimensions**: 150x150 pixels
- Reference: `AccountController::updateprofilePic()` (line 369-401)

### Blog Image Storage
- **Directory**: `storage/app/public/images/blogs-images/`
- **Default Image**: `images/blogs-images/default-image.jpg`
- Reference: `blogsController::uploadBlog()` (line 125-130)

### Document Upload
- **Supported Formats**: DOCX, PDF
- **Max Size**: 2048 KB
- **Processing**: Converted to HTML for storage
- Reference: `blogsController::uploadBlog()` (line 97-145)

---

## 15. Email Templates and Notifications

| Email Type | Trigger | Template | Reference |
|---|---|---|---|
| **Registration Confirmation** | User registration | `mail.register-mail` | `AccountController::processRegistration()` (line 74) |
| **Password Reset** | Forgot password request | `mail.forgot-password` | `AccountController::processForgotPassword()` (line 520) |
| **Password Change Notification** | Password reset completion | `mail.passwordNotification` | `AccountController::resetPasswordUpdate()` (line 593) |
| **Contact Form Notification** | Contact form submission | `mail.contactNotification` | `ContactFormController::submit()` (line 34) |

---

## 16. Database Schema Terminology

### User Table Fields

| Field | Type | Nullable | Unique | Purpose |
|---|---|---|---|---|
| id | BIGINT | No | Yes | Primary key |
| name | VARCHAR | No | No | User full name |
| email | VARCHAR | No | Yes | User email address |
| role | VARCHAR | No | No | User role (admin/broker/student) |
| email_verified_at | TIMESTAMP | Yes | No | Email verification timestamp |
| password | VARCHAR | No | No | Hashed password |
| image | VARCHAR | Yes | No | Profile picture filename |
| designation | VARCHAR | Yes | No | Professional title |
| mobile | VARCHAR | Yes | No | Phone number |
| remember_token | VARCHAR | Yes | No | Remember me token |
| created_at | TIMESTAMP | No | No | Record creation time |
| updated_at | TIMESTAMP | No | No | Last update time |

Additional fields (inferred from code):
- agentCode, dob, citizenship, residency, passportExpiry, passport, gender
- educationLevel, educationCountry, graduationStatus, institution, degree
- englishProficiency, englishListening, englishWriting, englishReading, englishSpeaking
- major, avgMark, majorInterest, higherEducationCountry1/2/3, educationLevelInterest

Reference: `database/migrations/0001_01_01_000000_create_users_table.php`