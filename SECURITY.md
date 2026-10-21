# Security Policy

## Supported Versions

Currently supported versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Best Practices

### 1. Credential Management

**Never commit sensitive credentials:**
- `.db_uri` - Contains database connection strings
- `.env` - Contains API keys and secrets
- Any files with API keys, passwords, or tokens

**Always use environment variables:**
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Database Security

**Connection Security:**
- Use SSL/TLS for database connections in production
- Example: `postgresql://user:pass@host:5432/db?sslmode=require`
- Never expose database ports publicly

**Migration Safety:**
- Review all migrations before applying
- Test in staging environment first
- Use compliance checks before production deployment
- Enable `ENFORCE_COMPLIANCE=true` in production

### 3. AI API Keys

**API Key Protection:**
- Store AI API keys in environment variables only
- Rotate API keys regularly (every 90 days recommended)
- Use separate API keys for dev/staging/production
- Monitor API usage for anomalies

**Cost Control:**
- Set budget alerts in OpenAI/Anthropic dashboards
- Use `--no-context` flag to reduce token usage
- Review generated migrations before applying

### 4. Application Security

**CORS Configuration:**
```bash
# Production: Set specific origins only
CORS_ORIGINS=https://yourdomain.com

# Development: Localhost only
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**API Security:**
- Add authentication middleware in production
- Implement rate limiting for AI generation endpoints
- Use HTTPS only in production
- Enable request logging and monitoring

### 5. File Permissions

**Restrict access to sensitive files:**
```bash
chmod 600 .db_uri .env
chmod 700 migrations/
```

### 6. Dependency Security

**Regular Updates:**
```bash
# Check for vulnerabilities
safety check

# Update dependencies
pip install --upgrade -r requirements.txt
```

**Automated Scanning:**
- GitHub Dependabot enabled
- Bandit security scanning in CI/CD
- Regular safety audits

## Reporting a Vulnerability

If you discover a security vulnerability, please follow these steps:

### 1. Do NOT create a public GitHub issue

Security vulnerabilities should be reported privately to protect users.

### 2. Email Security Team

Send details to: [Your security email here]

**Include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### 3. Response Timeline

- **24 hours:** Acknowledgment of report
- **7 days:** Initial assessment and severity classification
- **30 days:** Fix development and testing
- **45 days:** Public disclosure (coordinated)

### 4. Responsible Disclosure

We follow responsible disclosure practices:
- 90-day disclosure window from initial report
- Coordinated public disclosure
- Credit to reporter (if desired)
- Security advisory publication

## Security Features

### Built-in Protections

1. **Migration Compliance Enforcement**
   - Pre-flight validation
   - Destructive operation detection
   - Checksum verification

2. **Transaction Safety**
   - Automatic rollback on errors
   - DDL audit logging
   - State consistency checks

3. **Schema Interception**
   - Database triggers for unauthorized changes
   - Real-time monitoring
   - Audit trail

4. **Input Validation**
   - Pydantic models for API endpoints
   - SQL injection prevention
   - File type validation

### Security Checklist for Production

- [ ] All secrets in environment variables (not files)
- [ ] `.gitignore` properly configured
- [ ] HTTPS enabled for all endpoints
- [ ] CORS restricted to specific origins
- [ ] Database SSL/TLS enabled
- [ ] API authentication implemented
- [ ] Rate limiting configured
- [ ] Logging and monitoring enabled
- [ ] Regular security scans scheduled
- [ ] Backup and disaster recovery tested

## Known Security Considerations

### 1. AI-Generated Migrations

AI-generated migrations should always be reviewed by a human before applying:
- May contain logic errors
- Could include destructive operations
- Might not follow your schema conventions

**Mitigation:** Enable compliance checks and dry-run mode.

### 2. Python Migration Files

Python migrations execute arbitrary code:
- Review all `.py` migrations carefully
- Restrict migration directory permissions
- Consider disabling Python migrations in high-security environments

**Mitigation:** Use SQL migrations only, or implement code review process.

### 3. Database Triggers

DDL triggers monitor all schema changes:
- Can impact database performance
- May interfere with other tools
- Requires elevated database privileges

**Mitigation:** Test thoroughly in staging, monitor performance.

## Security Updates

Subscribe to security advisories:
- Watch this repository for security alerts
- Enable GitHub Dependabot
- Join our security mailing list: [Email]

## Compliance Frameworks

This system supports compliance with:
- SOC 2 (audit logging, access controls)
- HIPAA (data integrity, audit trails)
- PCI DSS (change management, logging)
- GDPR (data protection, audit requirements)

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Database](https://cwe.mitre.org/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security.html)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
