# PlusPoint EDU - Comprehensive Data Flow Documentation

## Executive Summary

This document provides a detailed analysis of data flows within the PlusPoint EDU application, a Laravel-based educational platform for international student admissions guidance. The system implements multiple interconnected data flows spanning user authentication, profile management, blog content management, referral code administration, and contact form handling.

---

## 1. Request/Response Flows for Key API Endpoints

### 1.1 Authentication Flows

#### 1.1.1 User Registration Flow

**Route Definition**: `routes/web.php` (line 28-29)
```
POST /account/process-register → AccountController::processRegistration()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.processRegistration()` in `app/Http/Controllers/AccountController.php` (line 33)
   - Receives form data: `name`, `email`, `password`, `confirm_password`, `role`, `agentCode`

2. **Validation** - `AccountController.processRegistration()` (line 34-59)
   - Validates email format (must be lowercase): `regex:/^[^A-Z]/`
   - Validates password strength: minimum 8 characters, at least one lowercase, one uppercase, one digit
   - Validates referral code against `code-database` table: `DB::table('code-database')->where('referral_code', $value)->exists()`
   - Returns JSON response with validation errors if validation fails

3. **User Creation** - `AccountController.processRegistration()` (line 61-68)
   - Creates new `User` model instance
   - Hashes password using `Hash::make($request->password)`
   - Stores user data in `users` table via `$user->save()`
   - User table schema defined in `database/migrations/0001_01_01_000000_create_users_table.php` (line 12-24)

4. **Email Notification** - `AccountController.processRegistration()` (line 69-71)
   - Calls `EmailController.SendRegisterEmail()` in `app/Http/Controllers/EmailController.php` (line 10)
   - Sends registration confirmation email via `Mail::to($toEmail)->send(new registration_mail())`
   - Mail template: `resources/views/mail/register-mail.blade.php`
   - Mail configuration: `config/mail.php` (line 14) - default mailer is `log` or SMTP based on `MAIL_MAILER` env

5. **Response** - `AccountController.processRegistration()` (line 73-80)
   - Returns JSON: `{"status": true, "errors": []}`
   - Sets session flash message: `'User has been registered successfully'`

#### 1.1.2 User Login Flow

**Route Definition**: `routes/web.php` (line 32)
```
POST /account/authenticate → AccountController::authenticate()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.authenticate()` in `app/Http/Controllers/AccountController.php` (line 83)
   - Receives: `email`, `password`

2. **Validation** - `AccountController.authenticate()` (line 84-88)
   - Validates email format and password presence
   - Uses Laravel's `Validator::make()`

3. **Authentication** - `AccountController.authenticate()` (line 89-90)
   - Calls `Auth::attempt(['email' => $request->email, 'password' => $request->password])`
   - Auth guard configured in `config/auth.php` (line 35-39) as `web` driver using `session`
   - User provider: `eloquent` model `App\Models\User` (line 60-63)

4. **Role-Based Redirect** - `AccountController.authenticate()` (line 91-103)
   - Admin users: redirect to `account.profile.admin`
   - Broker users: redirect to `account.profile`
   - Student users: redirect to `account.profile`
   - Invalid role: redirect back with error

5. **Session Management** - `config/session.php` (line 20)
   - Driver: `database` (stores sessions in `sessions` table)
   - Lifetime: 30 minutes (configurable via `SESSION_LIFETIME`)
   - Session table schema: `database/migrations/0001_01_01_000000_create_users_table.php` (line 26-33)

#### 1.1.3 Password Reset Flow

**Route Definition**: `routes/web.php` (line 35-36)
```
GET /account/forgot-password → AccountController::forgotPassword()
POST /account/process-forgot-password → AccountController::processForgotPassword()
```

**Data Flow Process**:

1. **Forgot Password Request** - `AccountController.processForgotPassword()` in `app/Http/Controllers/AccountController.php` (line 463)
   - Validates email exists in `users` table
   - Generates random token: `Str::random(60)` (line 469)

2. **Token Storage** - `AccountController.processForgotPassword()` (line 471-476)
   - Deletes existing tokens: `DB::table('password_reset_tokens')->where('email', $request->email)->delete()`
   - Inserts new token: `DB::table('password_reset_tokens')->insert([...])`
   - Token table schema: `database/migrations/0001_01_01_000000_create_users_table.php` (line 18-21)

3. **Email Dispatch** - `AccountController.processForgotPassword()` (line 477-483)
   - Creates mail data with token
   - Sends via `Mail::to($request->email)->send(new ResetPasswordEmail($mailData))`
   - Mail class: `app/Mail/ResetPasswordEmail.php` (line 27-29)
   - Template: `resources/views/mail/forgot-password.blade.php`

4. **Password Reset** - `AccountController.resetPasswordUpdate()` (line 506)
   - Retrieves token from `password_reset_tokens` table
   - Validates new password strength
   - Updates user password: `User::where('email', $tokenData->email)->first()->update(['password' => Hash::make($request->newPassword)])`
   - Deletes used token: `DB::table('password_reset_tokens')->where('email', $user->email)->delete()`
   - Sends confirmation email via `Mail::to($user->email)->send(new passwordNotification($mailData))`

### 1.2 User Profile Management Flows

#### 1.2.1 Profile Update Flow

**Route Definition**: `routes/web.php` (line 43)
```
PUT /account/update-profile → AccountController::updateProfile()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.updateProfile()` in `app/Http/Controllers/AccountController.php` (line 130)
   - Receives: `name`, `email`, `dob`, `citizenship`, `residency`, `passportExpiry`, `passport`, `gender`, `mobile`

2. **Validation** - `AccountController.updateProfile()` (line 131-142)
   - Validates date of birth: `before_or_equal:` 10 years ago
   - Validates unique email (excluding current user): `unique:users,email,{$id},id`
   - Validates unique passport: `unique:users,passport,{$id},id`

3. **Change Detection** - `AccountController.updateProfile()` (line 145-154)
   - Compares current user data with request data
   - Only updates if changes detected

4. **Database Update** - `AccountController.updateProfile()` (line 155-164)
   - Updates user record: `User::find($id)->update([...])`
   - Stores in `users` table

5. **Response** - `AccountController.updateProfile()` (line 165-175)
   - Returns JSON with status and errors
   - Sets session flash message

#### 1.2.2 Education Profile Update Flow

**Route Definition**: `routes/web.php` (line 44)
```
PUT /account/update-profile-edu → AccountController::updateProfileEdu()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.updateProfileEdu()` in `app/Http/Controllers/AccountController.php` (line 178)
   - Receives: `educationLevel`, `educationCountry`, `graduationStatus`, `institution`, `englishProficiency`, `avgMark`, `degree`, `major`

2. **Conditional Field Processing** - `AccountController.updateProfileEdu()` (line 205-215)
   - If education level is one of: Associate Degree, Bachelor's, Master's, Professional, Doctorate, Vocational → stores `degree`
   - If English proficiency is not 'NONE' → stores listening, writing, reading, speaking scores
   - Otherwise → sets these fields to null

3. **Database Update** - `AccountController.updateProfileEdu()` (line 216-224)
   - Updates `users` table with education data

#### 1.2.3 Preferences Profile Update Flow

**Route Definition**: `routes/web.php` (line 45)
```
PUT /account/update-profile-prefrences → AccountController::updateProfilePrefrences()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.updateProfilePrefrences()` in `app/Http/Controllers/AccountController.php` (line 237)
   - Receives: `higherEducationCountry1`, `higherEducationCountry2`, `higherEducationCountry3`, `majorInterest`, `educationLevelInterest`

2. **Database Update** - `AccountController.updateProfilePrefrences()` (line 248-254)
   - Updates `users` table with preference data

#### 1.2.4 Profile Picture Upload Flow

**Route Definition**: `routes/web.php` (line 46)
```
POST /account/update-profile-pic → AccountController::updateprofilePic()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.updateprofilePic()` in `app/Http/Controllers/AccountController.php` (line 267)
   - Receives: `image` file (optional if `nullCheckbox` present)

2. **Validation** - `AccountController.updateprofilePic()` (line 268-270)
   - Validates image: `image|mimes:jpeg,png,jpg,gif,svg|max:2048`

3. **File Storage** - `AccountController.updateprofilePic()` (line 277-281)
   - Stores original image: `$image->move(public_path('/profile_pic'), $imageName)`
   - File path: `public/profile_pic/{id}-{timestamp}.{ext}`

4. **Image Processing** - `AccountController.updateprofilePic()` (line 282-288)
   - Uses `Intervention\Image\ImageManager` with GD driver
   - Creates thumbnail: `$image->cover(150, 150)` (150x150 pixels)
   - Saves thumbnail: `public/profile_pic/thumb/{imageName}`

5. **Database Update** - `AccountController.updateprofilePic()` (line 289-290)
   - Updates `users` table: `image` column with filename

6. **Cleanup** - `AccountController.updateprofilePic()` (line 289-290)
   - Deletes old profile picture and thumbnail using `File::delete()`

### 1.3 Blog Management Flows

#### 1.3.1 Blog List and Filter Flow

**Route Definition**: `routes/web.php` (line 20)
```
GET /blogs → blogsController::index()
```

**Data Flow Process**:

1. **Request Reception** - `blogsController.index()` in `app/Http/Controllers/blogsController.php` (line 15)
   - Receives optional query parameter: `category`

2. **Category Fetch** - `blogsController.index()` (line 16)
   - Fetches all categories: `DB::table('blog_categories')->get()`

3. **Blog Query** - `blogsController.index()` (line 18-24)
   - Base query: `DB::table('blogs')`
   - If category selected: applies filter `where('category_id', $selectedCategory)`
   - Paginates results: `->paginate(9)` (9 blogs per page)

4. **Response** - `blogsController.index()` (line 27-32)
   - Returns view with: `category`, `blogs`, `selectedCategory`, `blogs_unpaginated`

#### 1.3.2 Blog Detail View Flow

**Route Definition**: `routes/web.php` (line 21)
```
GET /blog/{id} → blogsController::show()
```

**Data Flow Process**:

1. **Blog Fetch** - `blogsController.show()` in `app/Http/Controllers/blogsController.php` (line 35)
   - Queries: `DB::table('blogs')->where('id', $id)->first()`

2. **Content Decoding** - `blogsController.show()` (line 41)
   - Decodes HTML entities: `html_entity_decode($blog->content)`

3. **Response** - `blogsController.show()` (line 44)
   - Returns view with blog data

#### 1.3.3 Blog Upload Flow (Admin)

**Route Definition**: `routes/web.php` (line 51)
```
POST /profile/admin/portal/upload-blog → blogsController::uploadBlog()
```

**Data Flow Process**:

1. **Request Reception** - `blogsController.uploadBlog()` in `app/Http/Controllers/blogsController.php` (line 63)
   - Receives: `document` (DOCX or PDF), `title`, `category_id`, optional `image`

2. **Validation** - `blogsController.uploadBlog()` (line 65-70)
   - Document: `required|mimes:docx,pdf|max:2048`
   - Title: `required`
   - Category: `required`

3. **Document Processing** - `blogsController.uploadBlog()` (line 76-88)
   - **DOCX Files**: Uses `PhpOffice\PhpWord\IOFactory`
     - Loads document: `IOFactory::load($file->getPathname())`
     - Converts to HTML: `IOFactory::createWriter($phpWord, 'HTML')`
     - Captures output: `ob_start()` → `ob_get_clean()`
   - **PDF Files**: Uses `Smalot\PdfParser\Parser`
     - Parses PDF: `$parser->parseFile($file->getPathname())`
     - Extracts text: `$pdf->getText()`
     - Converts to HTML: `nl2br(e($text))`

4. **Image Handling** - `blogsController.uploadBlog()` (line 90-96)
   - If image provided: stores in `storage/app/public/images/blogs-images/`
   - Otherwise: uses default image path

5. **Database Storage** - `blogsController.uploadBlog()` (line 99-107)
   - Inserts into `blogs` table:
     - `title`: blog title
     - `content`: HTML content
     - `created_at`: current timestamp
     - `user_id`: authenticated user ID
     - `category_id`: selected category
     - `image`: image path

6. **Response** - `blogsController.uploadBlog()` (line 109)
   - Redirects back with success message

#### 1.3.4 Blog Category Addition Flow (Admin)

**Route Definition**: `routes/web.php` (line 50)
```
POST /profile/admin/portal/add-category → blogsController::addCategory()
```

**Data Flow Process**:

1. **Request Reception** - `blogsController.addCategory()` in `app/Http/Controllers/blogsController.php` (line 46)
   - Receives: `category_name`

2. **Validation** - `blogsController.addCategory()` (line 47-49)
   - Validates: `required|unique:blog_categories`

3. **Database Insert** - `blogsController.addCategory()` (line 51-54)
   - Inserts into `blog_categories` table
   - Sets `created_at` timestamp

4. **Response** - `blogsController.addCategory()` (line 56-59)
   - Fetches inserted category
   - Redirects with success message including category ID and name

#### 1.3.5 Blog Deletion Flow (Admin)

**Route Definition**: `routes/web.php` (line 52)
```
POST /profile/admin/portal/delete-blog/{id} → blogsController::deleteBlog()
```

**Data Flow Process**:

1. **Authorization Check** - `blogsController.deleteBlog()` in `app/Http/Controllers/blogsController.php` (line 111)
   - Verifies user is authenticated and has `admin` role

2. **Blog Deletion** - `blogsController.deleteBlog()` (line 116)
   - Deletes from `blogs` table: `DB::table('blogs')->where('id', $id)->delete()`

3. **Response** - `blogsController.deleteBlog()` (line 118)
   - Redirects to blogs page with success message

### 1.4 Contact Form Flow

**Route Definition**: `routes/web.php` (line 24)
```
POST /contact → ContactFormController::submit()
```

**Data Flow Process**:

1. **Request Reception** - `ContactFormController.submit()` in `app/Http/Controllers/ContactFormController.php` (line 10)
   - Receives: `name`, `email`, `message`, `country_code`, `mobile`

2. **Validation** - `ContactFormController.submit()` (line 14-21)
   - Validates: name, email format, message, mobile presence

3. **Mobile Number Concatenation** - `ContactFormController.submit()` (line 11)
   - Combines: `$country_code . $mobile`

4. **Email Dispatch** - `ContactFormController.submit()` (line 28-33)
   - Creates mail data with: `message`, `name`, `email`, `mobile`, `subject`
   - Sends to: `info@pluspoint.uk`
   - Mail class: `App\Mail\ContactMail` in `app/Mail/ContactMail.php` (line 10-20)
   - Template: `resources/views/mail/contactNotification.blade.php`

5. **Response** - `ContactFormController.submit()` (line 34)
   - Sets session flash: `'Thank you for your message! We will get back shortly.'`
   - Redirects back

### 1.5 Referral Code Management Flows

#### 1.5.1 Add Referral Code Flow (Admin)

**Route Definition**: `routes/web.php` (line 53)
```
POST /profile/admin/portal/add-referral-code → AccountController::addReferralCode()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.addReferralCode()` in `app/Http/Controllers/AccountController.php` (line 428)
   - Receives: `referral_code`, `description`

2. **Validation** - `AccountController.addReferralCode()` (line 429-432)
   - Validates: `referral_code` is required and unique in `code-database` table
   - Validates: `description` is required

3. **Database Insert** - `AccountController.addReferralCode()` (line 434-437)
   - Inserts into `code-database` table:
     - `referral_code`: the code
     - `description`: code description

4. **Response** - `AccountController.addReferralCode()` (line 439)
   - Redirects back with success message

#### 1.5.2 Delete Referral Code Flow (Admin)

**Route Definition**: `routes/web.php` (line 54)
```
POST /profile/admin/portal/delete-referral-code → AccountController::deleteReferralCode()
```

**Data Flow Process**:

1. **Request Reception** - `AccountController.deleteReferralCode()` in `app/Http/Controllers/AccountController.php` (line 442)
   - Receives: `referral_code_id`

2. **Validation** - `AccountController.deleteReferralCode()` (line 445-448)
   - Validates ID is present

3. **Database Delete** - `AccountController.deleteReferralCode()` (line 451)
   - Deletes from `code-database` table: `DB::table('code-database')->where('id', $id)->delete()`

4. **Response** - `AccountController.deleteReferralCode()` (line 453)
   - Redirects back with success message

### 1.6 User Export Flow

**Route Definition**: `routes/web.php` (line 55)
```
GET /profile/admin/updloaded-files/export-users → AccountController::export()
```

**Data Flow Process**:

1. **Export Initiation** - `AccountController.export()` in `app/Http/Controllers/AccountController.php` (line 556)
   - Generates timestamp: `Carbon::now()->format('Y-m-d_H-i-s')`
   - Creates filename: `users-{timestamp}.xlsx`

2. **Data Collection** - `UsersExport.collection()` in `app/Exports/UsersExport.php` (line 14)
   - Fetches all users: `User::all()`
   - Maps user data to array with 29 columns (line 15-44)

3. **Excel Generation** - `AccountController.export()` (line 557)
   - Uses `Maatwebsite\Excel\Facades\Excel::download()`
   - Applies headings from `UsersExport.headings()` (line 46-75)

4. **Response** - `AccountController.export()` (line 557)
   - Downloads XLSX file with user data

---

## 2. Data Transformations and Processing Pipelines

### 2.1 User Data Transformation Pipeline

**Registration to Profile Completion**:

1. **Initial Registration** - `AccountController.processRegistration()` (line 61-68)
   - Input: Basic user info (name, email, password, role, agentCode)
   - Storage: `users` table with minimal fields

2. **Profile Enrichment** - `AccountController.updateProfile()` (line 130-175)
   - Input: Personal details (DOB, citizenship, passport, gender, residency)
   - Transformation: Date validation, email/passport uniqueness check
   - Storage: Updates `users` table

3. **Education Data** - `AccountController.updateProfileEdu()` (line 178-224)
   - Input: Education level, institution, English proficiency scores
   - Transformation: Conditional field processing based on education level
   - Storage: Updates `users` table

4. **Preferences** - `AccountController.updateProfilePrefrences()` (line 237-254)
   - Input: Country preferences, major interest, education level interest
   - Storage: Updates `users` table

### 2.2 Blog Content Transformation Pipeline

**Document Upload to Display**:

1. **DOCX Processing** - `blogsController.uploadBlog()` (line 76-81)
   - Input: DOCX file
   - Process: 
     - Load with `PhpOffice\PhpWord\IOFactory::load()`
     - Convert to HTML with `IOFactory::createWriter($phpWord, 'HTML')`
     - Capture output buffer
   - Output: HTML string

2. **PDF Processing** - `blogsController.uploadBlog()` (line 82-88)
   - Input: PDF file
   - Process:
     - Parse with `Smalot\PdfParser\Parser::parseFile()`
     - Extract text with `$pdf->getText()`
     - Convert newlines to `<br>` tags: `nl2br(e($text))`
   - Output: HTML string

3. **HTML Entity Encoding** - `blogsController.uploadBlog()` (line 99-107)
   - Input: HTML content
   - Storage: Stores as-is in `blogs` table `content` column

4. **Display Decoding** - `blogsController.show()` (line 41)
   - Input: Encoded HTML from database
   - Process: `html_entity_decode($blog->content)`
   - Output: Rendered HTML

### 2.3 Image Processing Pipeline

**Profile Picture Upload**:

1. **File Reception** - `AccountController.updateprofilePic()` (line 267-270)
   - Input: Image file (JPEG, PNG, GIF, SVG, max 2MB)
   - Validation: MIME type and size checks

2. **File Storage** - `AccountController.updateprofilePic()` (line 277-281)
   - Process:
     - Generate filename: `{user_id}-{timestamp}.{extension}`
     - Move to: `public/profile_pic/{filename}`
   - Output: Stored file

3. **Thumbnail Generation** - `AccountController.updateprofilePic()` (line 282-288)
   - Input: Original image
   - Process:
     - Load with `ImageManager` (GD driver)
     - Cover/crop to 150x150: `$image->cover(150, 150)`
     - Save to: `public/profile_pic/thumb/{filename}`
   - Output: Thumbnail file

4. **Database Update** - `AccountController.updateprofilePic()` (line 289-290)
   - Stores filename in `users` table `image` column

5. **Cleanup** - `AccountController.updateprofilePic()` (line 289-290)
   - Deletes old files: `File::delete(public_path("/profile_pic/thumb/" . Auth::user()->image))`
   - Deletes old original: `File::delete(public_path("/profile_pic/" . Auth::user()->image))`

---

## 3. Event Flows and Messaging Patterns

### 3.1 Email Notification Flows

#### 3.1.1 Registration Confirmation Email

**Trigger**: `AccountController.processRegistration()` (line 69-71)

**Flow**:
1. Creates `EmailController` instance
2. Calls `EmailController.SendRegisterEmail($email, $name, $role)` (line 10)
3. Constructs mail data with user details
4. Sends via `Mail::to($toEmail)->send(new registration_mail($mailmessage, $subject, $mailrole))`
5. Mail class: `app/Mail/registration_mail.php` (line 12-58)
6. Template: `resources/views/mail/register-mail.blade.php`

**Mail Configuration**: `config/mail.php` (line 14)
- Default mailer: `env('MAIL_MAILER', 'log')`
- SMTP settings: host, port, encryption, username, password (lines 37-48)
- From address: `env('MAIL_FROM_ADDRESS', 'hello@example.com')`

#### 3.1.2 Password Reset Email

**Trigger**: `AccountController.processForgotPassword()` (line 477-483)

**Flow**:
1. Generates reset token: `Str::random(60)` (line 469)
2. Stores token in `password_reset_tokens` table (line 471-476)
3. Creates mail data with token
4. Sends via `Mail::to($request->email)->send(new ResetPasswordEmail($mailData))`
5. Mail class: `app/Mail/ResetPasswordEmail.php` (line 11-53)
6. Template: `resources/views/mail/forgot-password.blade.php`

#### 3.1.3 Password Change Confirmation Email

**Trigger**: `AccountController.resetPasswordUpdate()` (line 517-520)

**Flow**:
1. After password update
2. Sends via `Mail::to($user->email)->send(new passwordNotification($mailData))`
3. Mail class: `app/Mail/passwordNotification.php`
4. Template: `resources/views/mail/passwordNotification.blade.php`

#### 3.1.4 Contact Form Inquiry Email

**Trigger**: `ContactFormController.submit()` (line 28-33)

**Flow**:
1. Validates form data
2. Creates mail data with: name, email, message, mobile
3. Sends to: `info@pluspoint.uk`
4. Mail class: `app/Mail/ContactMail` (line 10-53)
5. Template: `resources/views/mail/contactNotification.blade.php`

### 3.2 Session Management Flow

**Configuration**: `config/session.php` (line 20)
- Driver: `database`
- Table: `sessions`
- Lifetime: 30 minutes
- Expire on close: true
- HTTP only: true
- Same-site: `lax`

**Session Storage Schema**: `database/migrations/0001_01_01_000000_create_users_table.php` (line 26-33)
```
- id (string, primary)
- user_id (foreign key, nullable)
- ip_address (string, nullable)
- user_agent (text, nullable)
- payload (longText)
- last_activity (integer, indexed)
```

**Flash Message Flow**:
1. Set: `session()->flash('success', 'Message')`
2. Store in session payload
3. Display in view
4. Auto-delete after next request

---

## 4. Integration Points with External Services

### 4.1 Email Service Integration

**Service**: SMTP Mail Server

**Configuration**: `config/mail.php` (lines 37-48)
- Host: `env('MAIL_HOST', '127.0.0.1')`
- Port: `env('MAIL_PORT', 2525)`
- Encryption: `env('MAIL_ENCRYPTION', 'tls')`
- Username: `env('MAIL_USERNAME')`
- Password: `env('MAIL_PASSWORD')`

**Integration Points**:
1. User registration confirmation
2. Password reset requests
3. Password change notifications
4. Contact form inquiries

**Mail Classes**:
- `app/Mail/registration_mail.php` - Registration confirmation
- `app/Mail/ResetPasswordEmail.php` - Password reset link
- `app/Mail/passwordNotification.php` - Password change confirmation
- `app/Mail/ContactMail.php` - Contact inquiry notification

### 4.2 File Storage Integration

**Configuration**: `config/filesystems.php` (lines 28-76)

**Disk Configurations**:

1. **Local Disk** (line 30-35)
   - Driver: `local`
   - Root: `storage/app`
   - Used for: Internal file storage

2. **Public Disk** (line 37-44)
   - Driver: `local`
   - Root: `storage/app/public`
   - URL: `{APP_URL}/storage`
   - Visibility: `public`
   - Used for: Blog images, profile pictures

3. **S3 Disk** (line 46-56)
   - Driver: `s3`
   - Key: `env('AWS_ACCESS_KEY_ID')`
   - Secret: `env('AWS_SECRET_ACCESS_KEY')`
   - Region: `env('AWS_DEFAULT_REGION')`
   - Bucket: `env('AWS_BUCKET')`
   - Optional integration for cloud storage

**Storage Usage**:
- Blog images: `storage/app/public/images/blogs-images/`
- Profile pictures: `public/profile_pic/`
- Profile thumbnails: `public/profile_pic/thumb/`

### 4.3 Document Processing Integration

**Libraries**:

1. **PhpOffice\PhpWord** - DOCX Processing
   - Used in: `blogsController.uploadBlog()` (line 76-81)
   - Functions: Load, convert to HTML

2. **Smalot\PdfParser** - PDF Processing
   - Used in: `blogsController.uploadBlog()` (line 82-88)
   - Functions: Parse, extract text

3. **Intervention\Image** - Image Processing
   - Used in: `AccountController.updateprofilePic()` (line 282-288)
   - Driver: GD
   - Functions: Cover/crop, save

---

## 5. Database Read/Write Patterns and Transactions

### 5.1 User Table Operations

**Table Schema**: `database/migrations/0001_01_01_000000_create_users_table.php` (line 12-24)

**Columns**:
- `id` (primary key)
- `name` (string)
- `email` (string, unique)
- `role` (string) - admin, broker, student
- `email_verified_at` (timestamp, nullable)
- `password` (string, hashed)
- `image` (string, nullable) - profile picture filename
- `designation` (string, nullable)
- `mobile` (string, nullable)
- `remember_token` (string, nullable)
- `timestamps` (created_at, updated_at)

**Extended Columns** (from profile updates):
- `dob` (date)
- `citizenship` (string)
- `residency` (string)
- `passportExpiry` (date)
- `passport` (string, unique)
- `gender` (string)
- `educationLevel` (string)
- `educationCountry` (string)
- `graduationStatus` (string)
- `institution` (string)
- `degree` (string, nullable)
- `englishProficiency` (string)
- `englishListening` (decimal, nullable)
- `englishWriting` (decimal, nullable)
- `englishReading` (decimal, nullable)
- `englishSpeaking` (decimal, nullable)
- `major` (string)
- `avgMark` (decimal)
- `majorInterest` (string)
- `higherEducationCountry1` (string)
- `higherEducationCountry2` (string)
- `higherEducationCountry3` (string)
- `educationLevelInterest` (string)
- `agentCode` (string, nullable)

**Write Operations**:

1. **User Creation** - `AccountController.processRegistration()` (line 61-68)
   ```
   INSERT INTO users (name, email, password, role, agentCode, created_at, updated_at)
   ```

2. **Profile Update** - `AccountController.updateProfile()` (line 155-164)
   ```
   UPDATE users SET name=?, email=?, mobile=?, dob=?, citizenship=?, passport=?, 
   passportExpiry=?, gender=?, residency=?, updated_at=? WHERE id=?
   ```

3. **Education Update** - `AccountController.updateProfileEdu()` (line 216-224)
   ```
   UPDATE users SET educationLevel=?, educationCountry=?, graduationStatus=?, 
   institution=?, degree=?, englishProficiency=?, englishListening=?, 
   englishWriting=?, englishReading=?, englishSpeaking=?, major=?, avgMark=?, updated_at=? WHERE id=?
   ```

4. **Preferences Update** - `AccountController.updateProfilePrefrences()` (line 248-254)
   ```
   UPDATE users SET higherEducationCountry1=?, higherEducationCountry2=?, 
   higherEducationCountry3=?, majorInterest=?, educationLevelInterest=?, updated_at=? WHERE id=?
   ```

5. **Password Update** - `AccountController.security()` (line 321)
   ```
   UPDATE users SET password=?, updated_at=? WHERE id=?
   ```

6. **Profile Picture Update** - `AccountController.updateprofilePic()` (line 289-290)
   ```
   UPDATE users SET image=?, updated_at=? WHERE id=?
   ```

**Read Operations**:

1. **User Fetch by ID** - `AccountController.profile()` (line 119)
   ```
   SELECT * FROM users WHERE id=? LIMIT 1
   ```

2. **User Fetch by Email** - `AccountController.authenticate()` (line 89-90)
   ```
   SELECT * FROM users WHERE email=? (via Auth::attempt)
   ```

3. **All Users Fetch** - `AccountController.adminUsersView()` (line 397)
   ```
   SELECT * FROM users
   ```

4. **User Export** - `UsersExport.collection()` (line 14)
   ```
   SELECT * FROM users (with all columns mapped)
   ```

### 5.2 Blog Table Operations

**Tables**:
- `blogs` - Blog content
- `blog_categories` - Blog categories

**Blogs Table Columns**:
- `id` (primary key)
- `title` (string)
- `content` (longText) - HTML content
- `user_id` (foreign key)
- `category_id` (foreign key)
- `image` (string) - image path
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Write Operations**:

1. **Blog Upload** - `blogsController.uploadBlog()` (line 99-107)
   ```
   INSERT INTO blogs (title, content, created_at, user_id, category_id, image)
   ```

2. **Category Addition** - `blogsController.addCategory()` (line 51-54)
   ```
   INSERT INTO blog_categories (category_name, created_at)
   ```

3. **Blog Deletion** - `blogsController.deleteBlog()` (line 116)
   ```
   DELETE FROM blogs WHERE id=?
   ```

**Read Operations**:

1. **All Categories** - `blogsController.index()` (line 16)
   ```
   SELECT * FROM blog_categories
   ```

2. **Blogs with Filter** - `blogsController.index()` (line 18-24)
   ```
   SELECT * FROM blogs WHERE category_id=? (optional) LIMIT 9 OFFSET ?
   ```

3. **Single Blog** - `blogsController.show()` (line 35)
   ```
   SELECT * FROM blogs WHERE id=? LIMIT 1
   ```

4. **Admin Blog List** - `blogsController.blogsAdmin()` (line 54)
   ```
   SELECT * FROM blogs ORDER BY id DESC LIMIT 5 OFFSET ?
   ```

### 5.3 Password Reset Token Operations

**Table Schema**: `database/migrations/0001_01_01_000000_create_users_table.php` (line 18-21)

**Columns**:
- `email` (string, primary key)
- `token` (string)
- `created_at` (timestamp, nullable)

**Write Operations**:

1. **Token Creation** - `AccountController.processForgotPassword()` (line 471-476)
   ```
   DELETE FROM password_reset_tokens WHERE email=?
   INSERT INTO password_reset_tokens (email, token, created_at)
   ```

2. **Token Deletion** - `AccountController.resetPasswordUpdate()` (line 516)
   ```
   DELETE FROM password_reset_tokens WHERE email=?
   ```

**Read Operations**:

1. **Token Verification** - `AccountController.resetPassword()` (line 499)
   ```
   SELECT * FROM password_reset_tokens WHERE token=? LIMIT 1
   ```

2. **Token Retrieval** - `AccountController.resetPasswordUpdate()` (line 506)
   ```
   SELECT * FROM password_reset_tokens WHERE token=? LIMIT 1
   ```

### 5.4 Referral Code Operations

**Table**: `code-database`

**Columns**:
- `id` (primary key)
- `referral_code` (string, unique)
- `description` (string)

**Write Operations**:

1. **Code Addition** - `AccountController.addReferralCode()` (line 434-437)
   ```
   INSERT INTO code-database (referral_code, description)
   ```

2. **Code Deletion** - `AccountController.deleteReferralCode()` (line 451)
   ```
   DELETE FROM code-database WHERE id=?
   ```

**Read Operations**:

1. **Code Validation** - `AccountController.processRegistration()` (line 51-54)
   ```
   SELECT EXISTS(SELECT 1 FROM code-database WHERE referral_code=?)
   ```

2. **All Codes** - `AccountController.adminPortalView()` (line 405)
   ```
   SELECT * FROM code-database
   ```

### 5.5 Session Table Operations

**Table Schema**: `database/migrations/0001_01_01_000000_create_users_table.php` (line 26-33)

**Write Operations**:

1. **Session Creation** - On login
   ```
   INSERT INTO sessions (id, user_id, ip_address, user_agent, payload, last_activity)
   ```

2. **Session Update** - On each request
   ```
   UPDATE sessions SET payload=?, last_activity=? WHERE id=?
   ```

3. **Session Deletion** - On logout or expiry
   ```
   DELETE FROM sessions WHERE id=?
   ```

### 5.6 Cache Table Operations

**Table Schema**: `database/migrations/0001_01_01_000001_create_cache_table.php` (line 12-24)

**Tables**:
- `cache` - Cache data
- `cache_locks` - Cache locks

**Cache Configuration**: `config/cache.php` (line 14)
- Default store: `env('CACHE_STORE', 'database')`
- Prefix: `env('CACHE_PREFIX', 'plus_point_education_cache_')`

**Write Operations**:

1. **Cache Set**
   ```
   INSERT INTO cache (key, value, expiration) VALUES (?, ?, ?)
   ON DUPLICATE KEY UPDATE value=?, expiration=?
   ```

2. **Cache Delete**
   ```
   DELETE FROM cache WHERE key=?
   ```

### 5.7 Job Queue Operations

**Table Schema**: `database/migrations/0001_01_01_000002_create_jobs_table.php` (line 12-57)

**Tables**:
- `jobs` - Job queue
- `job_batches` - Job batch tracking
- `failed_jobs` - Failed job logging

**Queue Configuration**: `config/queue.php` (line 14)
- Default connection: `env('QUEUE_CONNECTION', 'database')`
- Table: `env('DB_QUEUE_TABLE', 'jobs')`

**Write Operations**:

1. **Job Enqueue**
   ```
   INSERT INTO jobs (queue, payload, attempts, reserved_at, available_at, created_at)
   ```

2. **Job Dequeue**
   ```
   UPDATE jobs SET reserved_at=? WHERE id=? AND reserved_at IS NULL
   ```

3. **Job Completion**
   ```
   DELETE FROM jobs WHERE id=?
   ```

4. **Job Failure**
   ```
   INSERT INTO failed_jobs (uuid, connection, queue, payload, exception, failed_at)
   ```

---

## 6. State Management (Frontend and Backend)

### 6.1 Backend State Management

#### 6.1.1 Session-Based State

**Storage**: Database sessions table (configured in `config/session.php`)

**State Data**:
1. **Authentication State**
   - User ID: `Auth::id()`
   - User object: `Auth::user()`
   - Role: `Auth::user()->role`

2. **Flash Messages**
   - Success: `session()->flash('success', 'Message')`
   - Error: `session()->flash('error', 'Message')`
   - Info: `session()->flash('info', 'Message')`

**Lifecycle**:
- Created: On successful login via `Auth::attempt()`
- Updated: On each request
- Destroyed: On logout via `Auth::logout()` or session expiry (30 minutes)

#### 6.1.2 User State in Database

**User Profile State**:
- Basic info: name, email, role
- Personal details: DOB, citizenship, passport, gender, residency
- Education: level, country, institution, proficiency, marks
- Preferences: country preferences, major interest
- Media: profile picture filename

**State Transitions**:
1. Registration → Basic user created
2. Profile update → Personal details added
3. Education update → Education data added
4. Preferences update → Preferences added
5. Picture upload → Image filename stored

### 6.2 Frontend State Management

#### 6.2.1 View State

**Profile Views** - `resources/views/front/account/profiles/`

1. **Student Profile** - `student_profile.blade.php`
   - Displays: name, email, DOB, citizenship, passport, gender, residency
   - State source: User model passed from controller

2. **Education Profile** - `student_profile_edu.blade.php`
   - Displays: education level, institution, English proficiency, marks
   - State source: User model

3. **Preferences Profile** - `student_profile_prefrences.blade.php`
   - Displays: country preferences, major interest, education level interest
   - State source: User model

4. **Admin Profile** - `admin_profile.blade.php`
   - Displays: All users list
   - State source: Users collection from controller

5. **Blog Edit** - `blog-edit.blade.php`
   - Displays: Blog list, category list
   - State source: Blogs and categories from controller

#### 6.2.2 Form State

**Profile Update Forms**:
- Use `@csrf` token for CSRF protection
- Use `old()` helper to repopulate on validation error
- Display validation errors via `@error` directive

**Example**: `resources/views/front/account/profiles/student_profile.blade.php`
```
<input type="text" name="name" value="{{ old('name', $user->name) }}" />
@error('name')
    <span class="error">{{ $message }}</span>
@enderror
```

#### 6.2.3 Navigation State

**Sidebar Navigation** - `resources/views/front/account/sidebar.blade.php`
- Displays different menu items based on user role
- Active menu item highlighted based on current route

**View Composer State** - `app/Providers/AppServiceProvider.php` (line 23-28)
- Shares address categories with all views
- Fetches: `AddressCategory::with('addresses')->get()->groupBy('address_name')`
- Available in all views as `$categories`

### 6.3 Authentication State Management

**Guard Configuration**: `config/auth.php` (line 35-39)
- Guard: `web`
- Driver: `session`
- Provider: `users` (Eloquent model)

**Authentication Flow**:
1. User submits login form
2. `Auth::attempt()` verifies credentials
3. Session created with user ID
4. User object cached in memory for request
5. Subsequent requests load user from session

**Authorization Checks**:
- `Auth::check()` - Is user authenticated?
- `Auth::user()` - Get current user
- `Auth::user()->role` - Get user role
- Role-based redirects in controllers

---

## 7. Caching Strategies and Data Invalidation

### 7.1 Cache Configuration

**Default Store**: `config/cache.php` (line 14)
- Driver: `database`
- Table: `cache`
- Prefix: `plus_point_education_cache_`

**Available Stores**:
1. **Database** (default)
   - Connection: configurable via `DB_CACHE_CONNECTION`
   - Table: `cache`

2. **File**
   - Path: `storage/framework/cache/data`

3. **Redis** (optional)
   - Connection: `cache`
   - Lock connection: `default`

4. **Memcached** (optional)
   - Servers: configurable

### 7.2 View Caching

**Compiled Views**: `storage/framework/views/`
- Laravel automatically compiles Blade templates
- Cached on first request
- Invalidated on file change (in development)

**View Composer Caching** - `app/Providers/AppServiceProvider.php` (line 23-28)
```php
View::composer('*', function ($view) {
    $categories = AddressCategory::with('addresses')->get()->groupBy('address_name');
    $view->with('categories', $categories);
});
```
- Executes on every view render
- No explicit caching (queries database each time)
- Could be optimized with cache tags

### 7.3 Query Optimization

**Eager Loading**:
- `HomeController.index()` (line 13)
  ```php
  AddressCategory::with('addresses')->get()
  ```
  - Prevents N+1 queries
  - Loads categories and related addresses in 2 queries

**Pagination**:
- `blogsController.index()` (line 24)
  ```php
  $blogs = $blogsQuery->paginate(9)
  ```
  - Limits data per page
  - Reduces memory usage

### 7.4 Session Caching

**Session Storage**: Database
- Stored in `sessions` table
- Lifetime: 30 minutes (configurable)
- Auto-cleanup via session sweeper (2% chance per request)

**Session Payload**:
- Serialized PHP data
- Includes CSRF token
- Includes flash messages
- Includes authentication state

### 7.5 Cache Invalidation Strategies

**Manual Invalidation**:
- No explicit cache invalidation in current codebase
- All data reads directly from database

**Implicit Invalidation**:
1. **Session Expiry** - 30 minutes idle time
2. **Password Reset** - Deletes old tokens from `password_reset_tokens`
3. **File Deletion** - Removes old profile pictures

**Recommended Improvements**:
1. Cache address categories with TTL
2. Cache blog categories
3. Use cache tags for invalidation
4. Implement query result caching for frequently accessed data

---

## 8. File and Blob Storage Flows

### 8.1 Profile Picture Storage Flow

**Storage Location**: `public/profile_pic/`

**Flow**:

1. **Upload** - `AccountController.updateprofilePic()` (line 277-281)
   - Receives image file
   - Generates filename: `{user_id}-{timestamp}.{extension}`
   - Moves to: `public/profile_pic/{filename}`

2. **Thumbnail Generation** - `AccountController.updateprofilePic()` (line 282-288)
   - Reads original: `public/profile_pic/{filename}`
   - Processes with Intervention Image:
     - Driver: GD
     - Operation: `cover(150, 150)` - crops to 150x150
   - Saves to: `public/profile_pic/thumb/{filename}`

3. **Database Storage** - `AccountController.updateprofilePic()` (line 289-290)
   - Stores filename in `users` table `image` column

4. **Cleanup** - `AccountController.updateprofilePic()` (line 289-290)
   - Deletes old thumbnail: `File::delete(public_path("/profile_pic/thumb/" . Auth::user()->image))`
   - Deletes old original: `File::delete(public_path("/profile_pic/" . Auth::user()->image))`

5. **Deletion** - `AccountController.updateprofilePic()` (line 274-276)
   - If `nullCheckbox` present:
     - Sets `image` to null
     - Updates database: `User::where('id', $id)->update(['image' => null])`

### 8.2 Blog Image Storage Flow

**Storage Location**: `storage/app/public/images/blogs-images/`

**Flow**:

1. **Image Upload** - `blogsController.uploadBlog()` (line 90-96)
   - If image provided:
     - Stores: `$request->file('image')->store('images/blogs-images', 'public')`
     - Returns path: `images/blogs-images/{filename}`
   - If no image:
     - Uses default: `images/blogs-images/default-image.jpg`

2. **Database Storage** - `blogsController.uploadBlog()` (line 99-107)
   - Stores image path in `blogs` table `image` column

3. **Display** - `resources/views/front/blog-posts/blogs.blade.php`
   - Accesses via: `storage/images/blogs-images/{filename}`
   - URL: `{APP_URL}/storage/images/blogs-images/{filename}`

### 8.3 Document Upload Flow

**Supported Formats**: DOCX, PDF

**Storage**: Temporary during processing, content stored in database

**Flow**:

1. **DOCX Upload** - `blogsController.uploadBlog()` (line 76-81)
   - Receives DOCX file
   - Loads: `PhpOffice\PhpWord\IOFactory::load($file->getPathname())`
   - Converts to HTML: `IOFactory::createWriter($phpWord, 'HTML')`
   - Captures output: `ob_start()` → `ob_get_clean()`
   - Result: HTML string

2. **PDF Upload** - `blogsController.uploadBlog()` (line 82-88)
   - Receives PDF file
   - Parses: `Smalot\PdfParser\Parser::parseFile($file->getPathname())`
   - Extracts text: `$pdf->getText()`
   - Converts: `nl2br(e($text))` (newlines to `<br>`, escape HTML)
   - Result: HTML string

3. **Content Storage** - `blogsController.uploadBlog()` (line 99-107)
   - Stores HTML in `blogs` table `content` column (longText)
   - No file storage, only database storage

4. **Content Retrieval** - `blogsController.show()` (line 35-44)
   - Fetches from database: `DB::table('blogs')->where('id', $id)->first()`
   - Decodes HTML entities: `html_entity_decode($blog->content)`
   - Passes to view for rendering

### 8.4 File System Configuration

**Configuration**: `config/filesystems.php` (lines 28-76)

**Disk Setup**:

1. **Local Disk** (line 30-35)
   - Root: `storage/app`
   - Used for: Internal file operations

2. **Public Disk** (line 37-44)
   - Root: `storage/app/public`
   - URL: `{APP_URL}/storage`
   - Visibility: public
   - Used for: Blog images, accessible via web

3. **Symbolic Link** (line 70-72)
   - Links: `public/storage` → `storage/app/public`
   - Enables web access to storage files

### 8.5 File Cleanup Operations

**Profile Picture Cleanup** - `AccountController.updateprofilePic()` (line 289-290)
```php
File::delete(public_path("/profile_pic/thumb/" . Auth::user()->image));
File::delete(public_path("/profile_pic/" . Auth::user()->image));
```

**Triggers**:
1. When uploading new picture (deletes old files)
2. When deleting picture (sets to null)

**No Automatic Cleanup**:
- Orphaned files not automatically deleted
- Recommend implementing cleanup job for unused files

### 8.6 Export File Generation

**User Export** - `AccountController.export()` (line 556-557)

**Flow**:

1. **Data Collection** - `UsersExport.collection()` (line 14)
   - Fetches all users: `User::all()`
   - Maps to array with 29 columns

2. **Excel Generation** - `AccountController.export()` (line 557)
   - Uses `Maatwebsite\Excel\Facades\Excel::download()`
   - Applies headings from `UsersExport.headings()`
   - Generates XLSX file in memory

3. **File Download** - `AccountController.export()` (line 557)
   - Filename: `users-{Y-m-d_H-i-s}.xlsx`
   - Streams to client
   - No file storage on server

---

## 9. Data Validation and Error Handling

### 9.1 Input Validation Patterns

**Validation Framework**: Laravel's `Validator` facade

**Registration Validation** - `AccountController.processRegistration()` (line 34-59)
```php
$validator = Validator::make($request->all(), [
    'name' => 'required',
    'email' => 'required|email|regex:/^[^A-Z]/|unique:users,email',
    'password' => ['required', 'min:8', 'regex:/[a-z]/', 'regex:/[A-Z]/', 'regex:/[0-9]/'],
    'confirm_password' => 'required|same:password',
    'role' => 'required',
    'agentCode' => ['nullable', function ($attribute, $value, $fail) { ... }]
]);
```

**Custom Validation** - Referral code validation (line 51-54)
```php
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
```

**Profile Update Validation** - `AccountController.updateProfile()` (line 131-142)
```php
$validator = Validator::make($request->all(), [
    'name' => 'required|min:5',
    'email' => "required|email|unique:users,email,{$id},id",
    'dob' => "required|date|before_or_equal:" . date('Y-m-d', strtotime('-10 years')),
    'citizenship' => 'required',
    'residency' => 'required',
    'passportExpiry' => 'required',
    'passport' => "required|unique:users,passport,{$id},id",
    'gender' => 'required',
]);
```

**Contact Form Validation** - `ContactFormController.submit()` (line 14-21)
```php
$validator = Validator::make($request->all(), [
    'name' => 'required',
    'email' => 'required|email',
    'message' => 'required',
    'mobile' => 'required'
]);
```

**Blog Upload Validation** - `blogsController.uploadBlog()` (line 65-70)
```php
$validator = Validator::make($request->all(), [
    'document' => 'required|mimes:docx,pdf|max:2048',
    'title' => 'required',
    'category_id' => 'required',
]);
```

**Image Upload Validation** - `AccountController.updateprofilePic()` (line 268-270)
```php
$validator = Validator::make($request->all(), [
    'image' => $request->has('nullCheckbox') 
        ? 'nullable|image|mimes:jpeg,png,jpg,gif,svg|max:2048' 
        : 'required|image|mimes:jpeg,png,jpg,gif,svg|max:2048',
]);
```

### 9.2 Error Response Patterns

**JSON Response** - For AJAX requests
```php
return response()->json([
    'status' => false,
    'errors' => $validator->errors()
]);
```

**Redirect with Errors** - For form submissions
```php
return redirect()->back()
    ->withErrors($validator)
    ->withInput($request->only('email'));
```

**Session Flash** - For user feedback
```php
session()->flash('error', 'Invalid email or password');
session()->flash('success', 'User Profile Has Been Updated');
session()->flash('info', 'No changes were made to the user profile');
```

### 9.3 Error Handling

**404 Errors** - `blogsController.show()` (line 40)
```php
if (!$blog) {
    abort(404); // Return a 404 error if the blog is not found
}
```

**Authorization Checks** - `blogsController.deleteBlog()` (line 111)
```php
if (Auth::check() && Auth::user()->role == 'admin') {
    // Allow deletion
} else {
    return redirect()->route('account.login');
}
```

---

## 10. Summary of Data Flow Architecture

### 10.1 High-Level Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Browser / Client                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Laravel Web Application                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Route Layer (routes/web.php)               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Controller Layer (app/Http/Controllers/)         │   │
│  │  - AccountController (Auth, Profile, Admin)             │   │
│  │  - blogsController (Blog CRUD)                          │   │
│  │  - ContactFormController (Contact)                      │   │
│  │  - EmailController (Email dispatch)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          Model Layer (app/Models/)                       │   │
│  │  - User (Eloquent ORM)                                  │   │
│  │  - Address, AddressCategory                            │   │
│  │  - Post                                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        Service Layer (Mail, File, Image)                │   │
│  │  - Mail::send() → SMTP Server                           │   │
│  │  - File::move() → Local Storage                         │   │
│  │  - ImageManager → Image Processing                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        View Layer (resources/views/)                     │   │
│  │  - Blade Templates                                      │   │
│  │  - Form Rendering                                       │   │
│  │  - Data Display                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SMTP Server  │  │ File Storage │  │ Image Proc.  │          │
│  │ (Email)      │  │ (Local/S3)   │  │ (GD)         │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Database Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ users        │  │ blogs        │  │ sessions     │          │
│  │ (Profile)    │  │ (Content)    │  │ (State)      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ password_    │  │ blog_        │  │ code-        │          │
│  │ reset_tokens │  │ categories   │  │ database     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ cache        │  │ jobs         │  │ address*     │          │
│  │ (Caching)    │  │ (Queue)      │  │ (Lookup)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Key Data Flow Patterns

1. **Authentication Flow**
   - Request → Validation → Auth::attempt() → Session → Redirect

2. **Profile Update Flow**
   - Request → Validation → Change Detection → DB Update → Flash Message

3. **Blog Upload Flow**
   - Request → Validation → Document Processing → Image Storage → DB Insert

4. **Email Flow**
   - Trigger → Mail Data → Mail::send() → SMTP → Recipient

5. **File Storage Flow**
   - Upload → Validation → Move/Process → DB Reference → Cleanup

### 10.3 Data Consistency Mechanisms

1. **Unique Constraints**
   - Email: `unique:users,email`
   - Passport: `unique:users,passport`
   - Referral Code: `unique:code-database`

2. **Foreign Keys**
   - `user_id` in blogs table
   - `category_id` in blogs table
   - `user_id` in sessions table

3. **Validation Rules**
   - Password strength requirements
   - Date validations
   - Email format validation

4. **Transaction Safety**
   - Password reset: Delete old tokens before creating new ones
   - Profile picture: Delete old files before storing new ones

### 10.4 Performance Considerations

1. **Query Optimization**
   - Eager loading: `AddressCategory::with('addresses')`
   - Pagination: 9 blogs per page, 5 admin blogs per page

2. **Caching Opportunities**
   - Address categories (rarely change)
   - Blog categories (rarely change)
   - User profile data (per-user cache)

3. **File Storage**
   - Thumbnail generation for profile pictures
   - Document conversion to HTML (one-time)
   - Image storage in public directory for fast access

4. **Session Management**
   - 30-minute lifetime
   - Database storage (scalable)
   - HTTP-only cookies (security)

---

## Conclusion

The PlusPoint EDU application implements a comprehensive data flow architecture spanning user authentication, profile management, content management, and external service integration. The system uses Laravel's MVC pattern with database-backed sessions, file storage, and email notifications. Data flows are well-structured with validation at entry points, change detection for updates, and proper cleanup mechanisms for file management. The architecture supports multiple user roles (admin, broker, student) with role-based access control and provides extensive profile customization capabilities for international student guidance.