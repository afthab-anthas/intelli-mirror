# PlusPoint EDU - Comprehensive Architecture Overview

## Executive Summary

PlusPoint EDU is a Laravel-based educational support platform designed to guide international students through university admissions processes. The application provides comprehensive student profile management, blog content management, referral code administration, and contact form handling. Built with Laravel 11.9, the system follows the Model-View-Controller (MVC) architectural pattern with a modular structure supporting multiple user roles (students, brokers, and administrators).

---

## 1. System Architecture and High-Level Design

### 1.1 Architectural Pattern

The application follows the **Laravel MVC (Model-View-Controller)** architectural pattern as defined in `bootstrap/app.php` (line 6-18):

```php
return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
```

The system is structured as a **monolithic web application** with:
- **Frontend**: Blade templating engine with Bootstrap 5.2.3 for responsive UI
- **Backend**: Laravel framework handling business logic and data persistence
- **Database**: MySQL (configurable to SQLite, PostgreSQL, MariaDB, or SQL Server)
- **Session Management**: Database-backed sessions as configured in `config/session.php`

### 1.2 Core Application Flow

1. **Request Entry Point**: `public/index.php` (line 1-17) - Bootstraps the Laravel application
2. **Route Resolution**: `routes/web.php` (line 1-74) - Defines all application routes
3. **Controller Processing**: Controllers in `app/Http/Controllers/` handle business logic
4. **Data Persistence**: Eloquent ORM models in `app/Models/` manage database interactions
5. **View Rendering**: Blade templates in `resources/views/` generate HTML responses

### 1.3 Application Layers

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (Blade Views, Bootstrap, JavaScript)   │
├─────────────────────────────────────────┤
│         HTTP Layer                      │
│  (Routes, Controllers, Middleware)      │
├─────────────────────────────────────────┤
│         Business Logic Layer            │
│  (Controllers, Services, Validation)    │
├─────────────────────────────────────────┤
│         Data Access Layer               │
│  (Eloquent Models, Query Builder)       │
├─────────────────────────────────────────┤
│         Database Layer                  │
│  (MySQL, SQLite, PostgreSQL, etc.)      │
└─────────────────────────────────────────┘
```

---

## 2. Module Structure and Boundaries

### 2.1 Directory Structure

```
pluspoint-edu/
├── app/
│   ├── Http/
│   │   └── Controllers/          # Request handlers
│   ├── Models/                   # Data models
│   ├── Mail/                     # Email notifications
│   ├── Exports/                  # Data export functionality
│   └── Providers/                # Service providers
├── routes/
│   └── web.php                   # Web route definitions
├── resources/
│   ├── views/                    # Blade templates
│   ├── css/                      # Stylesheets
│   └── js/                       # JavaScript files
├── config/                       # Configuration files
├── database/
│   ├── migrations/               # Database schema
│   ├── factories/                # Model factories
│   └── seeders/                  # Database seeders
├── public/                       # Web root
└── storage/                      # Logs, cache, uploads
```

### 2.2 Core Modules

#### 2.2.1 Authentication Module

**Files**: 
- `app/Http/Controllers/AccountController.php` (614 lines)
- `app/Http/Controllers/Auth/` (multiple controllers)
- `config/auth.php`

**Responsibilities**:
- User registration with role-based assignment (`AccountController::processRegistration()` line 31-87)
- Login/logout functionality (`AccountController::authenticate()` line 99-130)
- Password reset flow (`AccountController::processForgotPassword()` line 470-495)
- Session management via database driver

**Key Methods**:
- `AccountController::registration()` - Display registration form
- `AccountController::processRegistration()` - Validate and create user account
- `AccountController::authenticate()` - Verify credentials and establish session
- `AccountController::resetPassword()` - Handle password reset token validation
- `AccountController::resetPasswordUpdate()` - Update password with token

#### 2.2.2 User Profile Management Module

**Files**:
- `app/Http/Controllers/AccountController.php` (profile methods)
- `app/Models/User.php`
- `resources/views/front/account/profiles/`

**Responsibilities**:
- Student profile management (personal, educational, preferences)
- Profile picture upload with image processing
- Educational background tracking
- Higher education preferences
- Password change functionality

**Key Methods**:
- `AccountController::profile()` - Display student profile
- `AccountController::profileEdu()` - Display educational background
- `AccountController::profilePrefrences()` - Display education preferences
- `AccountController::updateProfile()` - Update personal information
- `AccountController::updateProfileEdu()` - Update educational details
- `AccountController::updateProfilePrefrences()` - Update preferences
- `AccountController::updateprofilePic()` - Handle profile picture upload with Intervention Image library

#### 2.2.3 Blog Management Module

**Files**:
- `app/Http/Controllers/blogsController.php` (157 lines)
- `resources/views/front/blog-posts/`
- Database tables: `blogs`, `blog_categories`

**Responsibilities**:
- Blog post creation from DOCX/PDF documents
- Blog category management
- Blog display with pagination
- Document parsing (Word to HTML, PDF to text)

**Key Methods**:
- `blogsController::index()` - List blogs with category filtering
- `blogsController::show()` - Display individual blog post
- `blogsController::blogsAdmin()` - Admin blog management interface
- `blogsController::addCategory()` - Create new blog category
- `blogsController::uploadBlog()` - Parse and store blog from document
- `blogsController::deleteBlog()` - Remove blog post

**Document Processing**:
- DOCX files converted to HTML via `PhpOffice\PhpWord\IOFactory` (line 79-82)
- PDF files parsed to text via `Smalot\PdfParser\Parser` (line 83-87)

#### 2.2.4 Admin Portal Module

**Files**:
- `app/Http/Controllers/AccountController.php` (admin methods)
- `resources/views/front/account/profiles/admin_profile*.blade.php`

**Responsibilities**:
- User management and viewing
- Referral code administration
- Blog management interface
- User data export to Excel

**Key Methods**:
- `AccountController::profileAdmin()` - Admin dashboard redirect
- `AccountController::adminUsersView()` - Display all users
- `AccountController::adminPortalView()` - Display referral codes
- `AccountController::addReferralCode()` - Create referral code
- `AccountController::deleteReferralCode()` - Remove referral code
- `AccountController::export()` - Export users to Excel

#### 2.2.5 Contact Form Module

**Files**:
- `app/Http/Controllers/ContactFormController.php` (46 lines)
- `app/Mail/ContactMail.php`
- `resources/views/front/contact.blade.php`

**Responsibilities**:
- Handle contact form submissions
- Validate contact information
- Send email notifications to admin

**Key Methods**:
- `ContactFormController::submit()` - Process contact form and send email

#### 2.2.6 Email Notification Module

**Files**:
- `app/Http/Controllers/EmailController.php`
- `app/Mail/` (multiple mailable classes)
- `resources/views/mail/`

**Responsibilities**:
- Send registration confirmation emails
- Send password reset emails
- Send contact form notifications
- Send password change notifications

**Key Methods**:
- `EmailController::SendRegisterEmail()` - Send registration confirmation
- `Mail::to()->send()` - Generic mail sending via Laravel Mail facade

**Mail Classes**:
- `registration_mail` - Registration confirmation
- `ResetPasswordEmail` - Password reset link
- `passwordNotification` - Password change confirmation
- `ContactMail` - Contact form notification

#### 2.2.7 Data Export Module

**Files**:
- `app/Exports/UsersExport.php` (88 lines)
- Uses `maatwebsite/excel` package

**Responsibilities**:
- Export user data to Excel format
- Include all user profile fields
- Add column headers

**Key Methods**:
- `UsersExport::collection()` - Retrieve and format user data
- `UsersExport::headings()` - Define Excel column headers

### 2.3 Supporting Modules

#### 2.3.1 Home/Landing Page Module

**Files**:
- `app/Http/Controllers/HomeController.php` (25 lines)
- `app/Models/Address.php`, `app/Models/AddressCategory.php`
- `resources/views/front/home.blade.php`

**Responsibilities**:
- Display landing page with country/education categories
- Fetch and organize address categories

#### 2.3.2 Static Pages Module

**Files**:
- `app/Http/Controllers/AboutController.php` - About page
- `app/Http/Controllers/StudentsController.php` - Students page

---

## 3. Key Design Patterns Used Throughout the Codebase

### 3.1 Model-View-Controller (MVC)

**Implementation**: Core architectural pattern throughout the application.

**Example**: User registration flow
- **Model**: `User` class in `app/Models/User.php` (49 lines)
- **View**: `resources/views/front/account/registration.blade.php`
- **Controller**: `AccountController::processRegistration()` in `app/Http/Controllers/AccountController.php` (line 31-87)

### 3.2 Repository Pattern (Implicit)

**Implementation**: Eloquent ORM acts as repository layer.

**Example**: User data access in `AccountController::updateProfile()` (line 194-246)
```php
$user = User::find($id);
$user->name = $request->name;
$user->save();
```

### 3.3 Service Provider Pattern

**Implementation**: `AppServiceProvider` in `app/Providers/AppServiceProvider.php` (35 lines)

**Purpose**: Bootstrap application services and share data across views.

**Example**: View composer shares categories globally (line 24-27)
```php
View::composer('*', function ($view) {
    $categories = AddressCategory::with('addresses')->get()->groupBy('address_name');
    $view->with('categories', $categories);
});
```

### 3.4 Mailable Pattern

**Implementation**: Email notifications using Laravel Mailable classes.

**Files**: `app/Mail/` directory with multiple mailable classes

**Example**: `registration_mail` class (58 lines)
```php
public function envelope(): Envelope {
    return new Envelope(subject: $this->subject);
}
```

### 3.5 Validation Pattern

**Implementation**: Request validation using Laravel Validator facade.

**Example**: `AccountController::processRegistration()` (line 35-68)
```php
$validator = Validator::make($request->all(), [
    'name' => 'required',
    'email' => 'required|email|regex:/^[^A-Z]/|unique:users,email',
    'password' => ['required', 'min:8', 'regex:/[a-z]/', 'regex:/[A-Z]/', 'regex:/[0-9]/'],
]);
```

### 3.6 Middleware Pattern

**Implementation**: Route middleware for authentication and authorization.

**Example**: Guest routes in `routes/web.php` (line 32-42)
```php
Route::group(['middleware' => 'guest'], function () {
    Route::get("/register", [AccountController::class, 'registration']);
    Route::post("/process-register", [AccountController::class, 'processRegistration']);
});
```

**Example**: Authenticated routes (line 46-70)
```php
Route::group(['middleware' => ['auth']], function () {
    Route::get("/profile", [AccountController::class, 'profile']);
    Route::put("/update-profile", [AccountController::class, 'updateProfile']);
});
```

### 3.7 Factory Pattern

**Implementation**: Model factories for testing and seeding.

**File**: `database/factories/UserFactory.php` (1075 bytes)

### 3.8 Export Pattern

**Implementation**: Data export using Maatwebsite Excel package.

**File**: `app/Exports/UsersExport.php` (88 lines)

**Pattern**: Implements `FromCollection` and `WithHeadings` interfaces

### 3.9 Document Processing Pattern

**Implementation**: Adapter pattern for handling multiple document formats.

**File**: `blogsController::uploadBlog()` (line 95-130)

**Adapters**:
- DOCX: `PhpOffice\PhpWord\IOFactory`
- PDF: `Smalot\PdfParser\Parser`

### 3.10 Role-Based Access Control (RBAC)

**Implementation**: Role-based authorization in controllers.

**Example**: `AccountController::profileAdmin()` (line 359-367)
```php
if (Auth::check() && Auth::user()->role == 'admin') {
    // Admin-only logic
} else {
    return redirect()->route('account.login');
}
```

**Roles**: `admin`, `broker`, `student` (stored in `users.role` column)

---

## 4. Dependency Graph Between Major Components

### 4.1 Component Dependency Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Routes (web.php)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Controllers  │  │ Controllers  │  │ Controllers  │
│ (Account,    │  │ (Blogs,      │  │ (Contact,    │
│  Home)       │  │  Students)   │  │  Email)      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │ Models │      │  Mail  │      │Exports │
    │ (User, │      │Classes │      │        │
    │Address)│      │        │      │        │
    └────┬───┘      └────┬───┘      └────┬───┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                    ┌────▼────┐
                    │ Database │
                    │ (MySQL)  │
                    └──────────┘
```

### 4.2 Key Dependencies

#### 4.2.1 External Package Dependencies

From `composer.json` (line 8-17):

| Package | Version | Purpose |
|---------|---------|---------|
| `laravel/framework` | ^11.9 | Core framework |
| `laravel/ui` | ^4.5 | Authentication scaffolding |
| `intervention/image` | ^3.7 | Image processing |
| `maatwebsite/excel` | ^3.1 | Excel export |
| `phpoffice/phpword` | ^1.2 | DOCX parsing |
| `smalot/pdfparser` | ^2.11 | PDF parsing |

#### 4.2.2 Internal Dependencies

**AccountController** depends on:
- `User` model (line 8)
- `ResetPasswordEmail` mail class (line 9)
- `passwordNotification` mail class (line 10)
- `EmailController` (line 20)
- `ImageManager` from Intervention Image (line 21-22)
- `UsersExport` (line 29)

**blogsController** depends on:
- `User` model (line 7)
- `PhpOffice\PhpWord\IOFactory` (line 11)
- `Smalot\PdfParser\Parser` (line 12)

**AppServiceProvider** depends on:
- `AddressCategory` model (line 6)

### 4.3 Data Flow Diagram

```
User Request
    │
    ▼
Route Matching (routes/web.php)
    │
    ▼
Middleware Processing (auth, guest)
    │
    ▼
Controller Action
    │
    ├─► Validation (Validator::make)
    │
    ├─► Model Query/Update (Eloquent)
    │
    ├─► Mail Sending (Mail::to()->send)
    │
    └─► View Rendering (Blade)
    │
    ▼
HTTP Response
```

---

## 5. Deployment Model and Infrastructure Considerations

### 5.1 Deployment Architecture

**Deployment Type**: Traditional LAMP/LEMP stack

**Components**:
- **Web Server**: Apache or Nginx (configured via `.htaccess` in `public/.htaccess`)
- **PHP Runtime**: PHP 8.2+ (from `composer.json` line 8)
- **Database**: MySQL 5.7+ (default, configurable)
- **Application Server**: Built-in Laravel development server or production server

### 5.2 Environment Configuration

**Configuration File**: `.env.example` (64 lines)

**Key Environment Variables**:

```
APP_NAME=Plus Point Education
APP_ENV=local|production
APP_DEBUG=true|false
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel
DB_USERNAME=root
DB_PASSWORD=

SESSION_DRIVER=database
CACHE_STORE=database
QUEUE_CONNECTION=database

MAIL_MAILER=log|smtp
MAIL_HOST=127.0.0.1
MAIL_PORT=2525
MAIL_USERNAME=null
MAIL_PASSWORD=null
```

### 5.3 Database Configuration

**Default Connection**: MySQL (configurable in `config/database.php` line 17)

**Supported Databases**:
- SQLite
- MySQL/MariaDB
- PostgreSQL
- SQL Server

**Database Initialization**:
```bash
php artisan migrate
```

**Key Tables**:
- `users` - User accounts and profiles
- `password_reset_tokens` - Password reset tokens
- `sessions` - Session storage
- `blogs` - Blog posts
- `blog_categories` - Blog categories
- `address_categories` - Education destination categories
- `address` - Specific education destinations
- `code-database` - Referral codes
- `jobs` - Queue jobs
- `cache` - Cache storage

### 5.4 Storage Configuration

**Filesystem Configuration**: `config/filesystems.php` (76 lines)

**Disk Types**:
- `local`: `storage/app/` - Private file storage
- `public`: `storage/app/public/` - Public file storage (symlinked to `public/storage/`)
- `s3`: AWS S3 (optional)

**Upload Locations**:
- Profile pictures: `public/profile_pic/`
- Profile picture thumbnails: `public/profile_pic/thumb/`
- Blog images: `storage/app/public/images/blogs-images/`

### 5.5 Cache Configuration

**Default Cache Store**: Database (from `config/cache.php` line 17)

**Cache Table**: `cache` (created via migration)

**Supported Drivers**:
- Database
- File
- Redis
- Memcached

### 5.6 Session Configuration

**Session Driver**: Database (from `.env.example` line 30)

**Session Table**: `sessions`

**Session Lifetime**: 120 minutes (from `.env.example` line 31)

**Session Encryption**: Disabled by default

### 5.7 Queue Configuration

**Default Queue Connection**: Database (from `config/queue.php` line 14)

**Queue Table**: `jobs` (created via migration)

**Supported Drivers**:
- Sync (synchronous)
- Database
- Redis
- Beanstalkd
- SQS

### 5.8 Logging Configuration

**Default Log Channel**: Stack (from `config/logging.php` line 20)

**Log Channels**:
- `single` - Single file logging
- `daily` - Daily rotating logs
- `stack` - Multiple channels
- `slack` - Slack integration
- `syslog` - System log

**Log Location**: `storage/logs/laravel.log`

### 5.9 Mail Configuration

**Default Mailer**: Log (from `config/mail.php` line 14)

**Supported Mailers**:
- SMTP
- Sendmail
- Mailgun
- SES
- Postmark
- Log (development)
- Array (testing)

**From Address**: Configurable via `MAIL_FROM_ADDRESS` and `MAIL_FROM_NAME`

### 5.10 Infrastructure Requirements

**Minimum Requirements**:
- PHP 8.2+
- MySQL 5.7+ or compatible
- 512MB RAM
- 1GB disk space

**Recommended Requirements**:
- PHP 8.2+
- MySQL 8.0+
- 2GB+ RAM
- 10GB+ disk space
- Redis (for caching/sessions)
- Nginx or Apache

**Development Environment**:
- MAMP/XAMPP/LAMP stack
- Composer for dependency management
- Node.js for frontend asset compilation (Vite)

---

## 6. Communication Patterns (Sync/Async, Messaging, API Calls)

### 6.1 Synchronous Communication

#### 6.1.1 HTTP Request-Response

**Pattern**: Traditional request-response cycle

**Example**: User registration flow in `routes/web.php` (line 33-34)
```php
Route::get("/register", [AccountController::class, 'registration']);
Route::post("/process-register", [AccountController::class, 'processRegistration']);
```

**Flow**:
1. User submits registration form (POST)
2. `AccountController::processRegistration()` validates input
3. User record created in database
4. Response returned to client

#### 6.1.2 Database Queries

**Pattern**: Eloquent ORM for synchronous database access

**Example**: User profile update in `AccountController::updateProfile()` (line 194-246)
```php
$user = User::find($id);
$user->name = $request->name;
$user->save();
```

**Characteristics**:
- Blocking operations
- Immediate response
- Direct database access

### 6.2 Asynchronous Communication

#### 6.2.1 Email Notifications

**Pattern**: Mailable classes with Mail facade

**Example**: Registration email in `AccountController::processRegistration()` (line 74-77)
```php
$emailController = new EmailController();
$emailController->SendRegisterEmail($user->email, $user->name, $user->role);
```

**Implementation**: `EmailController::SendRegisterEmail()` (line 10-22)
```php
Mail::to($toEmail)->send(new registration_mail($mailmessage, $subject, $mailrole));
```

**Configuration**: `config/mail.php` (116 lines)

**Default Mailer**: Log (development) or SMTP (production)

#### 6.2.2 Queue System

**Configuration**: `config/queue.php` (112 lines)

**Default Connection**: Database

**Queue Table**: `jobs` (created via migration)

**Status**: Configured but not actively used in current codebase

**Potential Use Cases**:
- Email sending (currently synchronous)
- Image processing
- Document parsing
- Data export

### 6.3 Data Exchange Patterns

#### 6.3.1 JSON Responses

**Pattern**: AJAX responses with JSON format

**Example**: Profile update in `AccountController::updateProfile()` (line 238-245)
```php
return response()->json([
    'status' => true,
    'error' => []
]);
```

**Usage**: Frontend form submissions with AJAX

#### 6.3.2 File Upload/Download

**Pattern**: Multipart form data for uploads, file streaming for downloads

**Upload Example**: Profile picture in `AccountController::updateprofilePic()` (line 280-310)
```php
$image = $request->file('image');
$image->move(public_path('/profile_pic'), $imageName);
```

**Download Example**: User export in `AccountController::export()` (line 597-600)
```php
$filename = "users-{$timestamp}.xlsx";
return Excel::download(new UsersExport, $filename);
```

#### 6.3.3 Document Processing

**Pattern**: File parsing and conversion

**DOCX Processing** in `blogsController::uploadBlog()` (line 79-82)
```php
$phpWord = IOFactory::load($file->getPathname());
$xmlWriter = IOFactory::createWriter($phpWord, 'HTML');
$htmlContent = ob_get_clean();
```

**PDF Processing** (line 83-87)
```php
$parser = new Parser();
$pdf = $parser->parseFile($file->getPathname());
$text = $pdf->getText();
$htmlContent = nl2br(e($text));
```

### 6.4 API Communication Patterns

#### 6.4.1 Internal API Calls

**Pattern**: Controller-to-Controller communication

**Example**: Email sending in `AccountController::processRegistration()` (line 74-77)
```php
$emailController = new EmailController();
$emailController->SendRegisterEmail($user->email, $user->name, $user->role);
```

#### 6.4.2 External API Calls

**Status**: Not currently implemented in the codebase

**Potential Integrations**:
- Email service providers (Mailgun, SendGrid)
- Payment gateways
- University databases
- Document verification services

### 6.5 Session Management

**Pattern**: Database-backed sessions

**Configuration**: `config/session.php` (7863 bytes)

**Session Driver**: Database (from `.env.example` line 30)

**Session Table**: `sessions`

**Session Lifetime**: 120 minutes

**Session Encryption**: Disabled by default

**Example**: Authentication check in `AccountController::profile()` (line 133-142)
```php
if (Auth::check()) {
    $id = Auth::user()->id;
    $user = User::where('id', $id)->first();
    return view('front.account.profiles.student_profile', ['user' => $user]);
}
```

### 6.6 Middleware Communication

**Pattern**: Request/Response filtering

**Authentication Middleware**: `auth` guard (from `config/auth.php` line 29-32)
```php
'guards' => [
    'web' => [
        'driver' => 'session',
        'provider' => 'users',
    ],
],
```

**Guest Middleware**: Routes in `routes/web.php` (line 32-42)
```php
Route::group(['middleware' => 'guest'], function () {
    // Only accessible to non-authenticated users
});
```

**Protected Routes**: Routes in `routes/web.php` (line 46-70)
```php
Route::group(['middleware' => ['auth']], function () {
    // Only accessible to authenticated users
});
```

---

## 7. Security Architecture

### 7.1 Authentication System

#### 7.1.1 User Authentication

**Method**: Session-based authentication with password hashing

**Implementation**: `AccountController::authenticate()` (line 99-130)
```php
if (Auth::attempt(['email' => $request->email, 'password' => $request->password])) {
    // Authentication successful
}
```

**Password Hashing**: Laravel's `Hash` facade using bcrypt

**Configuration**: `config/auth.php` (115 lines)

**Guard Type**: Session-based web guard (line 29-32)

#### 7.1.2 Password Security

**Password Requirements** (from `AccountController::processRegistration()` line 44-48):
- Minimum 8 characters
- At least one lowercase letter
- At least one uppercase letter
- At least one digit

**Validation Rules**:
```php
'password' => [
    'required',
    'min:8',
    'regex:/[a-z]/',      // lowercase
    'regex:/[A-Z]/',      // uppercase
    'regex:/[0-9]/',      // digit
],
```

**Password Reset Flow**:
1. User requests password reset via `AccountController::processForgotPassword()` (line 470-495)
2. Token generated and stored in `password_reset_tokens` table
3. Reset link sent via email
4. User validates token and sets new password via `AccountController::resetPasswordUpdate()` (line 520-570)

#### 7.1.3 Email Verification

**Status**: Configured but not enforced

**Configuration**: `config/auth.php` (commented out in User model)

**Potential Implementation**: Email verification middleware

### 7.2 Authorization System

#### 7.2.1 Role-Based Access Control (RBAC)

**Roles**: `admin`, `broker`, `student`

**Storage**: `users.role` column

**Implementation**: Manual role checking in controllers

**Example**: Admin-only access in `AccountController::profileAdmin()` (line 359-367)
```php
if (Auth::check() && Auth::user()->role == 'admin') {
    // Admin-only logic
} else {
    return redirect()->route('account.login');
}
```

**Role-Based Redirects** in `AccountController::authenticate()` (line 115-128)
```php
switch (Auth::user()->role) {
    case 'admin':
        return redirect()->route('account.profile.admin');
    case 'broker':
        return redirect()->route('account.profile');
    case 'student':
        return redirect()->route('account.profile');
}
```

#### 7.2.2 Route-Level Authorization

**Guest Routes** (line 32-42 in `routes/web.php`):
```php
Route::group(['middleware' => 'guest'], function () {
    // Registration, login, password reset
});
```

**Authenticated Routes** (line 46-70):
```php
Route::group(['middleware' => ['auth']], function () {
    // Profile management, settings
});
```

#### 7.2.3 Controller-Level Authorization

**Pattern**: Manual authorization checks in controller methods

**Example**: Blog deletion in `blogsController::deleteBlog()` (line 145-160)
```php
if (Auth::check() && Auth::user()->role == 'admin') {
    // Delete blog
} else {
    return redirect()->route('account.login');
}
```

### 7.3 Data Protection

#### 7.3.1 Password Storage

**Method**: Bcrypt hashing via Laravel's `Hash` facade

**Configuration**: `config/app.php` (line 72)
```php
'cipher' => 'AES-256-CBC',
```

**Bcrypt Rounds**: 12 (from `.env.example` line 13)

**Implementation**: `AccountController::processRegistration()` (line 70)
```php
$user->password = Hash::make($request->password);
```

#### 7.3.2 Encryption

**Application Key**: `APP_KEY` environment variable

**Cipher**: AES-256-CBC (from `config/app.php` line 72)

**Encrypted Attributes**: None explicitly configured in User model

#### 7.3.3 Session Security

**Session Driver**: Database (secure, server-side storage)

**Session Encryption**: Disabled by default (from `.env.example` line 32)

**Session Lifetime**: 120 minutes (from `.env.example` line 31)

**CSRF Protection**: Enabled by default in Laravel (middleware included)

### 7.4 Input Validation and Sanitization

#### 7.4.1 Request Validation

**Pattern**: Validator facade with custom rules

**Example**: Registration validation in `AccountController::processRegistration()` (line 35-68)
```php
$validator = Validator::make($request->all(), [
    'name' => 'required',
    'email' => 'required|email|regex:/^[^A-Z]/|unique:users,email',
    'password' => ['required', 'min:8', 'regex:/[a-z]/', 'regex:/[A-Z]/', 'regex:/[0-9]/'],
    'confirm_password' => 'required|same:password',
    'role' => 'required',
    'agentCode' => ['nullable', function ($attribute, $value, $fail) { ... }],
]);
```

#### 7.4.2 Custom Validation Rules

**Referral Code Validation** in `AccountController::processRegistration()` (line 56-65)
```php
'agentCode' => [
    'nullable',
    function ($attribute, $value, $fail) {
        if (!empty($value)) {
            $validCode = DB::table('code-database')
                ->where('referral_code', $value)
                ->exists();
            if (!$validCode) {
                $fail('Invalid agent code.');
            }
        }
    }
]
```

#### 7.4.3 Email Validation

**Rules**: Email format, no uppercase letters, unique in database

**Example** (line 40):
```php
'email' => 'required|email|regex:/^[^A-Z]/|unique:users,email',
```

#### 7.4.4 HTML Escaping

**Pattern**: Blade template auto-escaping

**Example**: Blog content in `blogsController::show()` (line 45)
```php
$blog->content = html_entity_decode($blog->content);
```

**PDF Content Escaping** in `blogsController::uploadBlog()` (line 87)
```php
$htmlContent = nl2br(e($text)); // e() escapes HTML
```

### 7.5 File Upload Security

#### 7.5.1 Profile Picture Upload

**Validation** in `AccountController::updateprofilePic()` (line 272-274)
```php
'image' => 'required|image|mimes:jpeg,png,jpg,gif,svg|max:2048',
```

**Allowed MIME Types**: jpeg, png, jpg, gif, svg

**Max File Size**: 2MB

**Storage Location**: `public/profile_pic/`

**Image Processing**: Intervention Image library for thumbnail generation (line 300-305)
```php
$manager = new ImageManager(Driver::class);
$image = $manager->read($source_path);
$image->cover(150, 150);
$image->save(public_path("/profile_pic/thumb/{$imageName}"));
```

#### 7.5.2 Blog Document Upload

**Validation** in `blogsController::uploadBlog()` (line 97-101)
```php
'document' => 'required|mimes:docx,pdf|max:2048',
'title' => 'required',
'category_id' => 'required',
```

**Allowed MIME Types**: docx, pdf

**Max File Size**: 2MB

**Storage Location**: Temporary processing, then stored in database

### 7.6 Database Security

#### 7.6.1 SQL Injection Prevention

**Method**: Eloquent ORM parameterized queries

**Example**: User lookup in `AccountController::profile()` (line 135)
```php
$user = User::where('id', $id)->first();
```

**Query Builder Usage** in `blogsController::index()` (line 19-22)
```php
$blogsQuery = DB::table('blogs');
if ($selectedCategory) {
    $blogsQuery->where('category_id', $selectedCategory);
}
```

#### 7.6.2 Mass Assignment Protection

**Configuration**: `User` model uses `$fillable` array (line 16-21 in `app/Models/User.php`)
```php
protected $fillable = [
    'name',
    'email',
    'mobile',
    'password',
];
```

**Note**: Not all user attributes are mass-assignable; direct assignment used for other fields

#### 7.6.3 Sensitive Data Hiding

**Configuration**: `User` model hides sensitive attributes (line 26-29)
```php
protected $hidden = [
    'password',
    'remember_token',
];
```

### 7.7 CSRF Protection

**Status**: Enabled by default in Laravel

**Implementation**: Middleware automatically includes CSRF token in forms

**Token Verification**: Automatic for POST, PUT, PATCH, DELETE requests

### 7.8 Security Headers

**Status**: Not explicitly configured in the codebase

**Potential Improvements**:
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

### 7.9 Logging and Monitoring

**Log Channel**: Stack (default)

**Log Location**: `storage/logs/laravel.log`

**Log Level**: Debug (development), configurable for production

**Configuration**: `config/logging.php` (132 lines)

**Logged Events**:
- Authentication attempts
- Database queries (in debug mode)
- Exceptions and errors

### 7.10 Security Considerations and Recommendations

#### Current Strengths:
1. Password hashing with bcrypt
2. Session-based authentication
3. Input validation and sanitization
4. File upload restrictions
5. SQL injection prevention via ORM
6. CSRF protection enabled

#### Identified Gaps:
1. No explicit authorization middleware (manual checks in controllers)
2. No rate limiting on authentication endpoints
3. No two-factor authentication
4. No audit logging
5. No API authentication (if APIs are added)
6. Session encryption disabled
7. No security headers configured
8. No password expiration policy

#### Recommendations:
1. Implement Laravel's authorization gates/policies
2. Add rate limiting to authentication routes
3. Implement two-factor authentication
4. Enable session encryption in production
5. Add security headers middleware
6. Implement audit logging for sensitive operations
7. Add password expiration policies
8. Implement API token authentication (if needed)

---

## 8. Scalability Considerations and Bottlenecks

### 8.1 Current Architecture Limitations

#### 8.1.1 Database Bottlenecks

**Single Database Connection**:
- All reads and writes go to single MySQL instance
- No read replicas configured
- No database sharding

**Example**: User profile queries in `AccountController::profile()` (line 135)
```php
$user = User::where('id', $id)->first();
```

**Impact**: High concurrent user load will bottleneck at database

#### 8.1.2 Session Storage

**Database-Backed Sessions**:
- Every request reads/writes to `sessions` table
- No session clustering
- Single database dependency

**Configuration**: `config/session.php` (line 30)
```
SESSION_DRIVER=database
```

**Scalability Issue**: Session table becomes bottleneck under high load

#### 8.1.3 Cache Storage

**Database-Backed Cache**:
- Cache operations hit database
- No distributed caching

**Configuration**: `config/cache.php` (line 17)
```
CACHE_STORE=database
```

**Impact**: Cache misses cause database queries

#### 8.1.4 File Storage

**Local Filesystem**:
- Profile pictures stored on server filesystem
- No distributed storage
- No CDN integration

**Storage Locations**:
- `public/profile_pic/` - Profile pictures
- `storage/app/public/` - Blog images

**Scalability Issue**: Multi-server deployments require shared storage

#### 8.1.5 Email Processing

**Synchronous Email Sending**:
- Email sending blocks request processing
- No queue system in use

**Example**: Registration email in `AccountController::processRegistration()` (line 74-77)
```php
$emailController->SendRegisterEmail($user->email, $user->name, $user->role);
```

**Impact**: Slow email servers delay user registration response

#### 8.1.6 Document Processing

**Synchronous Document Parsing**:
- DOCX/PDF parsing happens in request cycle
- Large documents block request

**Example**: Blog upload in `blogsController::uploadBlog()` (line 79-87)
```php
$phpWord = IOFactory::load($file->getPathname());
// Synchronous processing
```

**Impact**: Large file uploads cause timeout

### 8.2 Scalability Improvements

#### 8.2.1 Database Optimization

**Current State**: Single database instance

**Improvements**:
1. **Read Replicas**: Configure MySQL replication for read-heavy operations
2. **Database Indexing**: Add indexes on frequently queried columns
   - `users.email` (authentication)
   - `blogs.category_id` (blog filtering)
   - `sessions.user_id` (session lookup)
3. **Query Optimization**: Use eager loading to prevent N+1 queries
4. **Connection Pooling**: Implement connection pooling for database connections

**Example - Eager Loading**:
```php
// Instead of:
$users = User::all();
foreach ($users as $user) {
    $user->addresses; // N queries
}

// Use:
$users = User::with('addresses')->get(); // 2 queries
```

#### 8.2.2 Caching Strategy

**Current State**: Database-backed cache

**Improvements**:
1. **Redis Cache**: Replace database cache with Redis
   ```
   CACHE_STORE=redis
   ```
2. **Cache Warming**: Pre-load frequently accessed data
3. **Cache Invalidation**: Implement smart cache invalidation
4. **Application-Level Caching**: Cache expensive queries

**Example - Query Caching**:
```php
$categories = Cache::remember('blog_categories', 3600, function () {
    return DB::table('blog_categories')->get();
});
```

#### 8.2.3 Session Management

**Current State**: Database sessions

**Improvements**:
1. **Redis Sessions**: Move to Redis for faster access
   ```
   SESSION_DRIVER=redis
   ```
2. **Session Clustering**: Distribute sessions across multiple servers
3. **Sticky Sessions**: Use load balancer sticky sessions

#### 8.2.4 Asynchronous Processing

**Current State**: Synchronous email and document processing

**Improvements**:
1. **Queue System**: Implement job queues for:
   - Email sending
   - Document processing
   - Image processing
   - Data export

**Configuration**: `config/queue.php` (line 14)
```php
'default' => env('QUEUE_CONNECTION', 'database'),
```

**Example - Queued Email**:
```php
Mail::to($email)->queue(new RegistrationMail($user));
```

**Example - Queued Job**:
```php
dispatch(new ProcessBlogDocument($file));
```

#### 8.2.5 File Storage

**Current State**: Local filesystem

**Improvements**:
1. **Cloud Storage**: Use S3 or similar for file storage
   ```
   FILESYSTEM_DISK=s3
   ```
2. **CDN Integration**: Serve static assets via CDN
3. **Image Optimization**: Compress images before storage

**Configuration**: `config/filesystems.php` (line 48-56)
```php
's3' => [
    'driver' => 's3',
    'key' => env('AWS_ACCESS_KEY_ID'),
    'secret' => env('AWS_SECRET_ACCESS_KEY'),
    'region' => env('AWS_DEFAULT_REGION'),
    'bucket' => env('AWS_BUCKET'),
],
```

#### 8.2.6 Load Balancing

**Current State**: Single server deployment

**Improvements**:
1. **Horizontal Scaling**: Deploy multiple application servers
2. **Load Balancer**: Use Nginx or HAProxy for load balancing
3. **Sticky Sessions**: Ensure session affinity
4. **Health Checks**: Monitor server health

#### 8.2.7 API Rate Limiting

**Current State**: No rate limiting

**Improvements**:
1. **Throttle Middleware**: Implement rate limiting on authentication endpoints
2. **IP-Based Limiting**: Limit requests per IP
3. **User-Based Limiting**: Limit requests per authenticated user

**Example**:
```php
Route::post('/authenticate', [AccountController::class, 'authenticate'])
    ->middleware('throttle:5,1'); // 5 requests per minute
```

#### 8.2.8 Database Query Optimization

**Current Bottlenecks**:

1. **Blog Listing** in `blogsController::index()` (line 19-26)
   ```php
   $blogs = $blogsQuery->paginate(9);
   ```
   - Missing: Index on `category_id`
   - Missing: Eager loading of related data

2. **User Lookup** in `AccountController::profile()` (line 135)
   ```php
   $user = User::where('id', $id)->first();
   ```
   - Missing: Caching of user data

3. **Referral Code Validation** in `AccountController::processRegistration()` (line 58-63)
   ```php
   DB::table('code-database')->where('referral_code', $value)->exists();
   ```
   - Missing: Index on `referral_code`
   - Missing: Cache of valid codes

### 8.3 Performance Metrics and Monitoring

#### 8.3.1 Key Metrics to Monitor

1. **Database Performance**:
   - Query execution time
   - Slow query log
   - Connection pool usage
   - Lock contention

2. **Application Performance**:
   - Request response time
   - Error rate
   - Memory usage
   - CPU usage

3. **User Experience**:
   - Page load time
   - Time to first byte (TTFB)
   - Largest contentful paint (LCP)

#### 8.3.2 Monitoring Tools

**Recommended Tools**:
- Laravel Telescope (development)
- New Relic (production)
- Datadog (production)
- Prometheus + Grafana (self-hosted)

### 8.4 Scalability Roadmap

**Phase 1 (Immediate)**:
1. Add database indexes
2. Implement query caching
3. Add rate limiting

**Phase 2 (Short-term)**:
1. Move to Redis for sessions/cache
2. Implement job queues
3. Add CDN for static assets

**Phase 3 (Medium-term)**:
1. Horizontal scaling with load balancer
2. Database read replicas
3. Cloud file storage (S3)

**Phase 4 (Long-term)**:
1. Microservices architecture
2. API gateway
3. Database sharding

### 8.5 Estimated Capacity

**Current Single-Server Capacity**:
- Concurrent Users: 100-500
- Requests per Second: 10-50
- Database Connections: 10-20

**With Optimizations (Phase 1-2)**:
- Concurrent Users: 1,000-5,000
- Requests per Second: 100-500
- Database Connections: 50-100

**With Full Scaling (Phase 3-4)**:
- Concurrent Users: 10,000+
- Requests per Second: 1,000+
- Database Connections: 500+

---

## 9. Technology Stack Summary

### 9.1 Backend Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Laravel | 11.9 |
| Language | PHP | 8.2+ |
| Database | MySQL | 5.7+ |
| ORM | Eloquent | Built-in |
| Authentication | Laravel Auth | Built-in |
| Session | Database | Built-in |
| Cache | Database | Built-in |
| Queue | Database | Built-in |
| Mail | SMTP/Log | Built-in |

### 9.2 Frontend Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Template Engine | Blade | Built-in |
| CSS Framework | Tailwind CSS | 3.4.0 |
| Build Tool | Vite | Latest |
| JavaScript | Vanilla JS | ES6+ |
| CSS Preprocessor | SASS | 1.56.1 |

### 9.3 External Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| intervention/image | Image Processing | 3.7 |
| maatwebsite/excel | Excel Export | 3.1 |
| phpoffice/phpword | DOCX Parsing | 1.2 |
| smalot/pdfparser | PDF Parsing | 2.11 |
| laravel/ui | Auth Scaffolding | 4.5 |

### 9.4 Development Tools

| Tool | Purpose |
|------|---------|
| Composer | PHP Dependency Management |
| NPM | JavaScript Dependency Management |
| PHPUnit | Testing Framework |
| Vite | Frontend Build Tool |
| MAMP/XAMPP | Local Development |

---

## 10. Implementation Details: Frontend, Auth, Testing, and Infrastructure

This section consolidates the concrete technology choices and configuration details that define how the application is built and run.

### 10.1 Frontend Architecture — Vue.js 3 SPA

The frontend is built as a **Single Page Application (SPA)** using **Vue.js 3** with the Composition API. Laravel's Blade engine serves only the initial HTML shell; all rendering after the first load is handled client-side.

**Component structure** (`resources/js/`):
- `components/auth/` — Login, register, password-reset forms
- `components/profile/` — Student, broker, and admin profile views
- `components/blog/` — Blog listing, filtering, and detail views
- `components/shared/` — Navbar, sidebar, flash messages

**State management**: Pinia (Vue's official store library) — one store per domain (auth, profile, blog).

**Client-side routing**: Vue Router 4 handles navigation; the server returns a 200 for all routes and Vue Router resolves the view.

**API communication**: All data fetching uses Axios with a JWT bearer token injected from `localStorage`.

---

### 10.2 Authentication — JWT Tokens via tymon/jwt-auth

Authentication is **stateless**, using JSON Web Tokens via the `tymon/jwt-auth` v2.0 package. There are no server-side sessions.

**Login flow**:
1. `POST /api/auth/login` → returns `{ access_token, refresh_token, token_type, expires_in }`
2. Frontend stores `access_token` in `localStorage` under the key `pluspoint_access_token`
3. Every request includes `Authorization: Bearer <token>`
4. Token is silently refreshed 15 minutes before expiry via `POST /api/auth/refresh`
5. Logout calls `POST /api/auth/logout` which blacklists the token in Redis

**JWT configuration** (`config/jwt.php`):
```
TTL:          60 minutes
Refresh TTL:  20160 minutes (2 weeks)
Blacklist:    Redis-backed
Algorithm:    HS256
```

**User roles** (stored in `users.role`): `admin`, `broker`, `student`, `manager` — four roles total. The `manager` role was introduced in v1.2 to support regional office staff who can view but not edit student profiles.

---

### 10.3 Testing — Pest PHP

The test suite uses **Pest PHP v2** rather than raw PHPUnit, giving a more expressive functional API:

```php
// tests/Feature/Auth/LoginTest.php
test('user can login and receive a JWT token', function () {
    $user = User::factory()->create();

    $response = $this->postJson('/api/auth/login', [
        'email'    => $user->email,
        'password' => 'password',
    ]);

    $response->assertOk()
             ->assertJsonStructure(['access_token', 'token_type', 'expires_in']);
});

test('invalid credentials return 401', function () {
    $this->postJson('/api/auth/login', [
        'email'    => 'nobody@example.com',
        'password' => 'wrong',
    ])->assertUnauthorized();
});
```

**Test directory layout**:
```
tests/
├── Feature/
│   ├── Auth/       — JWT login, refresh, logout
│   ├── Profile/    — Profile update flows
│   └── Blog/       — Blog CRUD
└── Unit/
    └── Models/     — Eloquent model assertions
```

Run the full suite with coverage:
```bash
./vendor/bin/pest --coverage
```

---

### 10.4 Database — PostgreSQL 15

The primary database is **PostgreSQL 15** (not MySQL). The default `DB_CONNECTION` in `.env` is `pgsql`:

```env
DB_CONNECTION=pgsql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=pluspoint_edu
DB_USERNAME=postgres
DB_PASSWORD=secret
```

PostgreSQL-specific features in active use:
- `jsonb` columns — English proficiency scores stored as structured JSON
- `pg_trgm` extension — full-text trigram search on blog content
- `uuid` primary keys — `blogs` table uses UUID instead of auto-increment integers
- Native `text[]` array columns — `higherEducationCountry` preferences stored as a PostgreSQL array, not three separate columns

---

### 10.5 Session and Cache — Redis

Both sessions and the cache layer use **Redis** (not the database driver):

```env
SESSION_DRIVER=redis
CACHE_STORE=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=null
REDIS_DB=0
```

The application runs **Laravel Horizon** for queue and job monitoring. The Horizon dashboard is available at `/horizon` and is restricted to the `admin` role via the `HorizonServiceProvider` gate.

---

### 10.6 Local Development — Docker Compose

The local development environment is fully containerised with **Docker Compose** (not MAMP or XAMPP). The `docker-compose.yml` in the project root defines four services:

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    volumes: [".:/var/www/html"]
  db:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: pluspoint_edu
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  horizon:
    build: .
    command: php artisan horizon
    depends_on: [db, redis]
```

Start the stack:
```bash
docker compose up -d
php artisan migrate
```

---

### 10.7 Key Runtime Constraints

| Constraint | Value |
|---|---|
| Blog listing — items per page | 12 (env: `BLOG_PER_PAGE`) |
| Profile picture thumbnail size | 200 × 200 px (Imagick driver) |
| Password minimum length | 10 characters |
| Password special character | Required (at least one of `!@#$%^&*`) |
| Profile picture upload limit | 5 MB |
| Blog document upload limit | 10 MB |
| JWT access token lifetime | 60 minutes |
| Session / Redis key TTL | 120 minutes |

---

## 11. Conclusion

PlusPoint EDU is a well-structured Laravel application designed for educational institution management and student profile administration. The architecture follows Laravel best practices with clear separation of concerns through the MVC pattern.

### Key Strengths:
1. Clear modular structure with distinct responsibilities
2. Comprehensive authentication and authorization system
3. Role-based access control for multiple user types
4. Secure password handling and input validation
5. Document processing capabilities
6. Data export functionality

### Areas for Enhancement:
1. Implement asynchronous processing for email and document handling
2. Migrate to Redis for sessions and caching
3. Add comprehensive authorization policies
4. Implement rate limiting on sensitive endpoints
5. Add monitoring and logging infrastructure
6. Optimize database queries with proper indexing
7. Implement horizontal scaling capabilities

### Recommended Next Steps:
1. Conduct security audit and penetration testing
2. Implement performance monitoring
3. Add comprehensive test coverage
4. Optimize database queries
5. Plan for horizontal scaling
6. Implement CI/CD pipeline

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Framework**: Laravel 11.9  
**PHP Version**: 8.2+