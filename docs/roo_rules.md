alwaysApply: true

# .cursorrules - pluspoint-edu

This .cursorrules file serves as the AI assistant knowledge index for the pluspoint-edu project.
Whenever working in Cursor, the following documents must be preloaded and treated as the base architectural context.

## Mandatory Reference Documents

[docs/architecture.md](docs/architecture.md) - System architecture and design patterns
[docs/structure.md](docs/structure.md) - Project organization and folder structure
[docs/code.md](docs/code.md) - Code patterns and conventions
[docs/dataflow.md](docs/dataflow.md) - Data flow and system boundaries
[docs/decisions.md](docs/decisions.md) - Architectural decisions and rationale
[docs/glossary.md](docs/glossary.md) - Domain terminology and definitions
[docs/risk.md](docs/risk.md) - Security and risk management

---

## Purpose of Mandatory Documentation

These documents collectively describe the complete context for pluspoint-edu development:

- **Architecture & Design Guidelines**: System design patterns, MVC structure, role-based access control (admin/broker/student)
- **Coding Standards & Patterns**: PHP/Laravel conventions, Blade templating, validation patterns, naming conventions
- **Data Flows & State Logic**: User authentication flows, profile management, blog management, referral code validation
- **Security & Risk Management**: Password hashing, CSRF protection, input validation, email verification, role-based authorization
- **Domain Terminology**: Educational platform concepts, student profiles, university applications, blog management

**Mandatory Reading**: All new features, debugging, refactoring, and enhancements must begin with reviewing these docs.

---

## Cursor Development Rules

### Context Management
- [ ] **Preload All Docs**: Parse all mandatory documentation before making recommendations
- [ ] **Single Source of Truth**: Treat docs as authoritative for architecture, standards, dataflows, and security
- [ ] **Cross-Check Ambiguities**: Verify unclear code details against documentation before assuming implementation details
- [ ] **No Hallucination**: Only suggest APIs, classes, methods, or logic that exist in the repository or are documented
- [ ] **Verification-First**: Use CodeTools-search_code and CodeTools-read_file before assuming details about the codebase

### Documentation & Code Alignment
- [ ] **Update Docs with Features**: All new features must update relevant /docs files as part of completion
- [ ] **Consistency Required**: All changes must align with architecture.md, structure.md, and code.md standards
- [ ] **Task Breakdown**: Break down complex tasks with [ ], [x], [-] markers for tracking progress
- [ ] **Clear Rationale**: Document architectural decisions in decisions.md when adding new patterns

### Security & Performance
- [ ] **Security Checks**: Analyze authentication, authorization, input validation, and secrets management for every change
- [ ] **Token Usage**: Verify CSRF tokens are present in forms and AJAX requests
- [ ] **Password Security**: Ensure passwords use Hash::make() and validation includes complexity requirements
- [ ] **Email Validation**: Validate email format and uniqueness constraints
- [ ] **Performance Checks**: Evaluate database query efficiency, N+1 problems, and caching opportunities
- [ ] **File Upload Safety**: Validate file types, sizes, and storage paths for user uploads

---

## Project-Specific Verification Rules

### Technology Stack
- **Backend**: Laravel 11.9+ (PHP 8.2+)
- **Frontend**: Blade templates, Bootstrap 5, jQuery 3.6, Vanilla JavaScript
- **Database**: MySQL with Eloquent ORM
- **Build Tools**: Vite, npm, Composer
- **Key Packages**: 
  - `intervention/image` (v3.7) - Image processing
  - `maatwebsite/excel` (v3.1) - Excel export
  - `phpoffice/phpword` (v1.2) - Word document parsing
  - `smalot/pdfparser` (v2.11) - PDF parsing
  - `laravel/ui` (v4.5) - Authentication scaffolding

### Code Quality Standards

#### PHP/Laravel Conventions
- [ ] Use PSR-4 autoloading (App\\ namespace)
- [ ] Controllers in `app/Http/Controllers/` with PascalCase names
- [ ] Models in `app/Models/` extending Eloquent
- [ ] Use Eloquent ORM for database queries (prefer over raw SQL)
- [ ] Implement validation using `Validator::make()` with custom error messages
- [ ] Use Laravel's built-in authentication with `Auth::` facade
- [ ] Implement role-based access control: admin, broker, student
- [ ] Use `Hash::make()` for password hashing with BCRYPT_ROUNDS=12
- [ ] Implement middleware for route protection (@auth, guest middleware)
- [ ] Use named routes with `route()` helper for URLs
- [ ] Implement CSRF protection with `@csrf` in forms
- [ ] Use session flashing for user feedback: `session()->flash()`

#### Blade Template Conventions
- [ ] Use `@auth` and `@guest` directives for conditional rendering
- [ ] Use `{{ }}` for output escaping, `{!! !!}` only for trusted HTML
- [ ] Implement role-based UI: `auth()->user()->role == 'admin'`
- [ ] Use `@yield()` for template inheritance
- [ ] Use `@foreach` for loops with proper null checks
- [ ] Include CSRF token in all forms: `@csrf`
- [ ] Use Bootstrap 5 classes for responsive design
- [ ] Implement form validation error display with `$errors->has()`

#### JavaScript/jQuery Conventions
- [ ] Use AJAX with CSRF token headers: `X-CSRF-TOKEN`
- [ ] Implement form submission with `$.ajax()` for JSON responses
- [ ] Use `FormData` for file uploads
- [ ] Validate client-side before server submission
- [ ] Handle error responses with proper user feedback
- [ ] Use Bootstrap modals for dialogs
- [ ] Implement AOS (Animate On Scroll) for animations

#### Database Conventions
- [ ] Use migrations for schema changes
- [ ] Use Eloquent relationships (hasMany, belongsTo)
- [ ] Implement soft deletes where appropriate
- [ ] Use timestamps (created_at, updated_at) on all tables
- [ ] Use foreign keys for referential integrity
- [ ] Index frequently queried columns

### Development Workflow

#### Branch Strategy
- [ ] Use feature branches: `feature/feature-name`
- [ ] Use bugfix branches: `bugfix/issue-name`
- [ ] Merge to main only after testing

#### Commit Standards
- [ ] Use descriptive commit messages: `[Feature/Fix/Docs] Description`
- [ ] Include issue/task reference when applicable
- [ ] Keep commits atomic and focused
- [ ] No debug code or console.log in commits

#### PR Requirements
- [ ] All tests passing (PHPUnit)
- [ ] Code follows PSR-12 standards
- [ ] Documentation updated
- [ ] No hardcoded credentials or secrets
- [ ] Performance impact assessed

### Technology-Specific Guidelines

#### Laravel Best Practices
- [ ] Use route model binding for resource routes
- [ ] Implement resource controllers for CRUD operations
- [ ] Use form requests for complex validation
- [ ] Implement service classes for business logic
- [ ] Use events and listeners for decoupled operations
- [ ] Implement query scopes for reusable query logic
- [ ] Use database transactions for multi-step operations
- [ ] Implement proper error handling with try-catch

#### Authentication & Authorization
- [ ] Use `Auth::check()` to verify authentication
- [ ] Use `Auth::user()` to get current user
- [ ] Implement role-based middleware for protected routes
- [ ] Use `Auth::attempt()` for login authentication
- [ ] Implement password reset with token validation
- [ ] Use `Hash::check()` for password verification
- [ ] Implement email verification where required
- [ ] Use session-based authentication (not API tokens)

#### File Handling
- [ ] Store uploads in `storage/app/public/` or `public/` directories
- [ ] Validate file types: MIME type checking
- [ ] Validate file sizes: max 2MB for images, 2MB for documents
- [ ] Generate unique filenames to prevent collisions
- [ ] Use Intervention Image for image processing
- [ ] Use PhpOffice for Word document parsing
- [ ] Use Smalot PdfParser for PDF parsing
- [ ] Implement proper error handling for file operations

#### Email Handling
- [ ] Use Laravel Mail facade: `Mail::to()->send()`
- [ ] Implement Mailable classes in `app/Mail/`
- [ ] Use Blade templates for email content
- [ ] Include proper email headers and formatting
- [ ] Test emails in development with `MAIL_MAILER=log`
- [ ] Implement queue jobs for bulk emails

### Security Requirements

#### Authentication & Authorization
- [ ] Implement role-based access control (RBAC)
- [ ] Validate user roles before sensitive operations
- [ ] Use middleware for route protection
- [ ] Implement proper session management
- [ ] Use secure password hashing (BCRYPT_ROUNDS=12)
- [ ] Implement password complexity validation:
  - Minimum 8 characters
  - At least one lowercase letter
  - At least one uppercase letter
  - At least one digit

#### Data Protection
- [ ] Validate all user inputs (email format, length, type)
- [ ] Sanitize output to prevent XSS
- [ ] Use parameterized queries (Eloquent) to prevent SQL injection
- [ ] Implement CSRF protection on all forms
- [ ] Hash sensitive data (passwords, tokens)
- [ ] Use HTTPS in production
- [ ] Implement rate limiting for login attempts
- [ ] Validate file uploads (type, size, content)

#### Secrets Management
- [ ] Never commit `.env` files
- [ ] Use `.env.example` for configuration template
- [ ] Store secrets in environment variables
- [ ] Use `env()` helper to access secrets
- [ ] Rotate API keys and tokens regularly
- [ ] Implement proper error messages (no sensitive data leakage)

#### Dependency Management
- [ ] Keep dependencies updated
- [ ] Review security advisories regularly
- [ ] Use `composer audit` to check for vulnerabilities
- [ ] Implement proper error handling for external APIs
- [ ] Validate external API responses

### Performance Guidelines

#### Frontend Performance
- [ ] Lazy load images with `lazyload` library
- [ ] Minimize CSS/JavaScript files
- [ ] Use Bootstrap CDN for faster delivery
- [ ] Implement pagination for large datasets (9 items per page for blogs)
- [ ] Cache static assets
- [ ] Optimize image sizes and formats
- [ ] Minimize DOM manipulation in JavaScript
- [ ] Use event delegation for dynamic elements

#### Backend Performance
- [ ] Use database indexes on frequently queried columns
- [ ] Implement pagination for list queries
- [ ] Use eager loading to prevent N+1 queries
- [ ] Cache frequently accessed data
- [ ] Optimize database queries
- [ ] Use query builder for complex queries
- [ ] Implement proper database transactions
- [ ] Monitor query performance

#### Database Optimization
- [ ] Index foreign keys
- [ ] Index columns used in WHERE clauses
- [ ] Use pagination (9 items per page for blogs)
- [ ] Avoid SELECT * queries
- [ ] Use eager loading with `with()`
- [ ] Implement query caching where appropriate

---

## Verification Checklist

### Before Committing Code

#### Compilation & Syntax
- [ ] PHP syntax is valid (no parse errors)
- [ ] Blade templates compile without errors
- [ ] JavaScript has no syntax errors
- [ ] CSS is valid
- [ ] No undefined variables or functions

#### Code Quality
- [ ] Code follows PSR-12 standards
- [ ] No debug statements (dd(), var_dump(), console.log())
- [ ] No commented-out code blocks
- [ ] Proper indentation and formatting
- [ ] No trailing whitespace
- [ ] Meaningful variable and function names

#### Security
- [ ] No hardcoded credentials or secrets
- [ ] CSRF tokens present in forms
- [ ] Input validation implemented
- [ ] Output properly escaped
- [ ] No SQL injection vulnerabilities
- [ ] File uploads validated
- [ ] Authentication checks in place

#### Testing
- [ ] Unit tests pass: `php artisan test`
- [ ] Feature tests pass
- [ ] Manual testing completed
- [ ] Edge cases tested
- [ ] Error scenarios tested

### Before Submitting PR

#### Functionality
- [ ] Feature works as specified
- [ ] All acceptance criteria met
- [ ] No regressions in existing features
- [ ] Edge cases handled
- [ ] Error messages are user-friendly

#### Testing
- [ ] Test coverage meets requirements (>80%)
- [ ] All tests passing
- [ ] Manual testing completed
- [ ] Cross-browser testing done
- [ ] Mobile responsiveness verified

#### Code Review Checklist
- [ ] Code follows project conventions
- [ ] No code duplication
- [ ] Proper error handling
- [ ] Logging implemented where needed
- [ ] Performance impact assessed
- [ ] Security implications reviewed
- [ ] Database migrations included
- [ ] Backward compatibility maintained

#### Documentation
- [ ] README updated if needed
- [ ] API documentation updated
- [ ] Architecture documentation updated
- [ ] CHANGELOG updated
- [ ] Code comments added for complex logic
- [ ] Inline documentation for public methods

### Documentation Requirements

#### Code Documentation
- [ ] Class docblocks with description
- [ ] Method docblocks with parameters and return types
- [ ] Complex logic explained with comments
- [ ] TODO comments tracked and resolved
- [ ] Deprecated code marked with @deprecated

#### Architecture Documentation
- [ ] New patterns documented in architecture.md
- [ ] Data flow diagrams updated
- [ ] Database schema changes documented
- [ ] API endpoints documented
- [ ] Configuration options documented

#### User Documentation
- [ ] User-facing features documented
- [ ] Setup instructions updated
- [ ] Troubleshooting guide updated
- [ ] FAQ updated if applicable

### Security Verification

#### Input Validation
- [ ] All user inputs validated
- [ ] Email format validated
- [ ] File types validated
- [ ] File sizes validated
- [ ] String lengths validated
- [ ] Numeric ranges validated

#### Authentication & Authorization
- [ ] Login functionality tested
- [ ] Password reset tested
- [ ] Role-based access verified
- [ ] Session management tested
- [ ] Logout functionality tested

#### Data Protection
- [ ] Passwords hashed with Hash::make()
- [ ] Sensitive data not logged
- [ ] CSRF tokens present
- [ ] XSS protection implemented
- [ ] SQL injection prevention verified

#### Secrets Management
- [ ] No secrets in code
- [ ] Environment variables used
- [ ] .env file not committed
- [ ] API keys rotated
- [ ] Database credentials secured

### Performance Validation

#### Load Testing
- [ ] Page load time acceptable (<3s)
- [ ] Database queries optimized
- [ ] No N+1 query problems
- [ ] Pagination implemented for large datasets
- [ ] Caching implemented where appropriate

#### Query Optimization
- [ ] Database indexes present
- [ ] Eager loading used
- [ ] Query count minimized
- [ ] Complex queries optimized
- [ ] Slow queries identified and fixed

#### Frontend Optimization
- [ ] Images lazy loaded
- [ ] CSS/JS minified
- [ ] Bundle size acceptable
- [ ] Animations smooth (60fps)
- [ ] No memory leaks

### Code Review Checklist

#### Conventions & Standards
- [ ] Follows PSR-12 coding standards
- [ ] Follows Laravel conventions
- [ ] Follows project naming conventions
- [ ] Consistent with existing code style
- [ ] No code duplication

#### Maintainability
- [ ] Code is readable and understandable
- [ ] Complex logic explained
- [ ] Functions have single responsibility
- [ ] Classes have single responsibility
- [ ] Proper abstraction levels

#### Error Handling
- [ ] Try-catch blocks for exceptions
- [ ] Proper error messages
- [ ] User-friendly error display
- [ ] Logging of errors
- [ ] Graceful degradation

#### Logging & Monitoring
- [ ] Important events logged
- [ ] Error conditions logged
- [ ] No sensitive data in logs
- [ ] Log levels appropriate
- [ ] Monitoring alerts configured

### Pre-Deployment

#### CI/CD Pipeline
- [ ] All tests passing
- [ ] Code quality checks passing
- [ ] Security scans passing
- [ ] Build successful
- [ ] Deployment pipeline verified

#### Staging Testing
- [ ] Feature tested in staging
- [ ] Database migrations tested
- [ ] Email functionality tested
- [ ] File uploads tested
- [ ] Third-party integrations tested

#### Database Migrations
- [ ] Migrations created for schema changes
- [ ] Rollback tested
- [ ] Data migration tested
- [ ] Backup created
- [ ] Migration order verified

#### Deployment Plan
- [ ] Rollback plan documented
- [ ] Deployment steps documented
- [ ] Downtime minimized
- [ ] Monitoring configured
- [ ] Communication plan ready

### Post-Deployment

#### Health Checks
- [ ] Application starts successfully
- [ ] Database connections working
- [ ] Email service working
- [ ] File uploads working
- [ ] Authentication working

#### Error Monitoring
- [ ] Error rates normal
- [ ] No new exceptions
- [ ] Performance metrics normal
- [ ] User reports monitored
- [ ] Logs reviewed

#### Performance Metrics
- [ ] Page load times acceptable
- [ ] Database query times acceptable
- [ ] Memory usage normal
- [ ] CPU usage normal
- [ ] Error rates acceptable

#### User Acceptance
- [ ] Feature works as expected
- [ ] No user-facing errors
- [ ] Performance acceptable
- [ ] UI/UX as designed
- [ ] Feedback collected

---

## Project-Specific Context

### Application Domain
- **Purpose**: Educational support platform for international university admissions
- **Target Users**: Students, brokers/agents, administrators
- **Key Features**: User authentication, profile management, blog management, referral codes, admin dashboard
- **Supported Countries**: UK, Germany, Romania, Canada, Australia, New Zealand, Singapore, Malaysia, UAE, India

### User Roles & Permissions
- **Admin**: Full system access, user management, blog management, referral code management
- **Broker**: Student profile management, application tracking
- **Student**: Profile management, application tracking, preference management

### Database Schema Key Tables
- `users` - User accounts with roles (admin/broker/student)
- `password_reset_tokens` - Password reset token management
- `sessions` - Session management
- `blogs` - Blog content with categories
- `blog_categories` - Blog categorization
- `code-database` - Referral codes for agent registration

### Key Features
- User registration with role selection and agent code validation
- Multi-step profile completion (personal, educational, preferences)
- Blog management with document parsing (DOCX, PDF)
- Admin dashboard for user and referral code management
- Email notifications (registration, password reset, contact form)
- Profile picture management with image processing
- User data export to Excel

### Common Patterns in Codebase

#### Validation Pattern
```php
$validator = Validator::make($request->all(), [
    'field' => 'required|rule1|rule2',
    'email' => 'required|email|unique:users,email',
    'password' => ['required', 'min:8', 'regex:/[a-z]/', 'regex:/[A-Z]/', 'regex:/[0-9]/'],
]);

if ($validator->passes()) {
    // Process valid data
} else {
    return response()->json(['status' => false, 'errors' => $validator->errors()]);
}
```

#### Authentication Pattern
```php
if (Auth::check()) {
    $user = Auth::user();
    if ($user->role == 'admin') {
        // Admin-specific logic
    }
} else {
    return redirect()->route('account.login');
}
```

#### AJAX Form Submission Pattern
```javascript
$.ajaxSetup({
    headers: {'X-CSRF-TOKEN': $('meta[name="csrf-token"]').attr('content')}
});

$("#form").submit(function(e) {
    e.preventDefault();
    $.ajax({
        type: 'POST',
        url: "{{ route('route.name') }}",
        data: $(this).serialize(),
        dataType: 'json',
        success: function(response) {
            if (response.status) {
                // Handle success
            } else {
                // Handle errors
            }
        }
    });
});
```

#### Email Notification Pattern
```php
$mailData = ['key' => 'value'];
Mail::to($email)->send(new MailableClass($mailData));
```

---

## Critical Rules for AI Assistance

1. **PRESERVE** all existing documentation links - do NOT remove or modify them
2. **VERIFY** code patterns against actual codebase before suggesting changes
3. **ENFORCE** role-based access control in all features
4. **VALIDATE** all user inputs with appropriate rules
5. **HASH** all passwords with Hash::make()
6. **PROTECT** all forms with @csrf tokens
7. **ESCAPE** all output in Blade templates
8. **TEST** all changes before committing
9. **DOCUMENT** all architectural decisions
10. **MONITOR** security and performance implications

---

## Success Criteria

- Cursor must not operate without context docs loaded
- All decisions rely on the context packs
- Features are only "done" if both code and /docs are updated
- No unsupported assumptions; verify context across packs
- Enterprise-grade, security-conscious, performance-optimized solutions always proposed
- Role-based access control enforced in all features
- All user inputs validated and sanitized
- All sensitive operations logged and monitored
```

This comprehensive .cursorrules file provides:

1. **Preserved existing documentation links** at the top
2. **Purpose section** explaining why docs are mandatory
3. **Cursor Development Rules** for AI-assisted development
4. **Project-Specific Verification Rules** based on actual codebase analysis:
   - Technology stack (Laravel 11, PHP 8.2, MySQL, Bootstrap 5)
   - Code quality standards (PSR-12, Blade conventions, validation patterns)
   - Development workflow (branching, commits, PRs)
   - Security requirements (RBAC, password hashing, CSRF protection)
   - Performance guidelines (pagination, lazy loading, query optimization)

5. **Comprehensive Verification Checklists** for:
   - Pre-commit (syntax, security, testing)
   - Pre-PR (functionality, testing, documentation)
   - Pre-deployment (CI/CD, staging, migrations)
   - Post-deployment (health checks, monitoring)

6. **Project-Specific Context** including:
   - Application domain and user roles
   - Database schema overview
   - Key features and common patterns
   - Critical rules for AI assistance

The file is enterprise-grade, security-conscious, and tailored to the pluspoint-edu project's actual tech stack and conventions.