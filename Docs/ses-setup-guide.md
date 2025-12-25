# AWS SES Setup Guide

This guide describes how to set up AWS Simple Email Service (SES) for use with the Turkspot email service. This setup is required before SES can be used for sending outreach emails.

## Overview

AWS SES setup involves:
1. AWS SES account configuration
2. Domain verification (SPF, DKIM, DMARC)
3. Production access request (to move out of sandbox mode)
4. Testing email deliverability

## Prerequisites

- AWS account with access to SES
- Domain name (e.g., `turkspot.nl`) with access to DNS records
- Administrative access to DNS provider

---

## Step 1: AWS SES Account Setup

### 1.1 Access AWS SES Console

1. Log in to AWS Console
2. Navigate to **Simple Email Service (SES)**
3. Select your preferred AWS region (recommended: `eu-west-1` for EU-based services)

### 1.2 Verify Email Address (Sandbox Mode)

In sandbox mode, you can only send emails to verified email addresses. For initial testing:

1. Go to **Verified identities** in SES console
2. Click **Create identity**
3. Select **Email address**
4. Enter email address to verify
5. Click **Create identity**
6. Check email inbox and click verification link

**Note**: This is only for testing. You'll need domain verification for production use.

---

## Step 2: Domain Verification

To send emails from your domain (e.g., `noreply@turkspot.nl`), you need to verify your domain and configure DNS records.

### 2.1 Verify Domain in SES

1. In SES console, go to **Verified identities**
2. Click **Create identity**
3. Select **Domain**
4. Enter your domain name (e.g., `turkspot.nl`)
5. Select **Use a default MAIL FROM domain** (recommended) or customize
6. Click **Create identity**

### 2.2 Configure DNS Records

After creating the domain identity, SES will provide DNS records that need to be added to your domain's DNS configuration.

#### 2.2.1 Verification Record (Required)

**Purpose**: Proves you own the domain

**Record Type**: TXT
**Name**: `_amazonses.turkspot.nl` (or as shown in SES console)
**Value**: Provided by SES (starts with `amazonses:`)

**How to add**:
1. Log in to your DNS provider (e.g., Cloudflare, Route53, etc.)
2. Add TXT record with name and value from SES console
3. Wait for DNS propagation (usually 5-60 minutes)
4. Return to SES console and click **Verify**

#### 2.2.2 SPF Record (Required)

**Purpose**: Authorizes SES to send emails on behalf of your domain

**Record Type**: TXT
**Name**: `turkspot.nl` (root domain)
**Value**: `v=spf1 include:amazonses.com ~all`

**If SPF record already exists**: Add `include:amazonses.com` to the existing record:
```
v=spf1 include:amazonses.com include:other-provider.com ~all
```

#### 2.2.3 DKIM Records (Required for Deliverability)

**Purpose**: Email authentication to prevent spoofing and improve deliverability

**Record Type**: CNAME (3 records provided by SES)

SES provides 3 CNAME records that need to be added to DNS:
- Name: `xxxxxxxxxx._domainkey.turkspot.nl`
- Value: `xxxxxxxxxx.dkim.amazonses.com`

**How to add**:
1. Add all 3 CNAME records provided by SES
2. Wait for DNS propagation
3. SES will automatically enable DKIM signing once records are verified (may take up to 72 hours)

#### 2.2.4 DMARC Record (Recommended)

**Purpose**: Policy for handling emails that fail SPF/DKIM authentication

**Record Type**: TXT
**Name**: `_dmarc.turkspot.nl`
**Value**: `v=DMARC1; p=none; rua=mailto:dmarc-reports@turkspot.nl`

**Explanation**:
- `p=none`: Don't reject emails that fail authentication (good for initial setup)
- `rua`: Email address for DMARC aggregate reports (optional)

**For production**: Consider changing to `p=quarantine` or `p=reject` after monitoring.

---

## Step 3: Production Access Request

By default, SES starts in **sandbox mode**, which limits you to:
- Sending only to verified email addresses
- 200 emails per day
- 1 email per second

For outreach emails, you need **production access**.

### 3.1 Request Production Access

1. In SES console, go to **Account dashboard**
2. Click **Request production access**
3. Fill out the request form:

**Mail Type**: Transactional
**Website URL**: `https://turkspot.nl`
**Use case description**:
```
Service notifications for location owners on Turkspot platform.

We send informational emails to business owners to notify them that their 
location has been added to our platform. These are transactional service 
notifications, not marketing emails.

Emails include:
- One-time notification when location is added to platform
- Claim confirmation emails (after business owner claims their location)
- Claim rejection emails (if claim is rejected by admin)

We follow AVG/GDPR compliance:
- Only public contact information is used
- Opt-out links are included in all emails
- No marketing content
- Clear service notification purpose
```

**Expected sending volume**:
- Start: ~50 emails per day
- Growth: Scaling to 250-500 emails per day over 6 months
- Peak: Maximum 500 emails per day

**Do you have a process to handle bounces and complaints?**: Yes
- We track bounce and complaint rates
- Invalid emails are removed from our system
- We respect opt-out requests immediately

4. Submit the request

### 3.2 Review Time

- **Typical review time**: 24-48 hours
- AWS may request additional information
- You'll receive email notification when access is granted

### 3.3 After Approval

Once approved:
- Sandbox restrictions are removed
- You can send to any email address
- Rate limits are increased (typically 200 emails/second, 50,000/day for new accounts)
- Start with conservative sending rates to build reputation

---

## Step 4: Testing Email Deliverability

### 4.1 Initial Testing

1. Send test email via SES console or API
2. Check spam folder (initially emails may be flagged)
3. Verify SPF/DKIM authentication using email headers

### 4.2 Email Authentication Testing

Use tools to verify email authentication:

- **mail-tester.com**: 
  1. Send test email to address provided by mail-tester
  2. Check score (aim for 8+/10)
  3. Review authentication results (SPF, DKIM, DMARC)

- **MXToolbox** (https://mxtoolbox.com/):
  - SPF Check: `https://mxtoolbox.com/spf.aspx`
  - DKIM Check: `https://mxtoolbox.com/dkim.aspx`
  - DMARC Check: `https://mxtoolbox.com/dmarc.aspx`

### 4.3 Monitor Sending Statistics

In SES console, monitor:
- **Sending quota**: Daily sending limit
- **Sending rate**: Emails per second
- **Reputation metrics**: Bounce rate, complaint rate
- **Bounce and complaint notifications**: Set up SNS topics for monitoring

**Target metrics**:
- Bounce rate: < 5%
- Complaint rate: < 0.1%
- Keep sending volume consistent to build reputation

---

## Step 5: Configuration Variables

After SES setup, configure the following environment variables:

```bash
# Email Provider
EMAIL_PROVIDER=ses  # or 'smtp' for fallback

# AWS SES Configuration
AWS_SES_REGION=eu-west-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Or use IAM role (if running on AWS infrastructure)
# Leave AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY empty to use default credentials
```

### 5.1 IAM Permissions

If using IAM role or user, ensure it has the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    }
  ]
}
```

For production, consider restricting `Resource` to your verified domain.

---

## Step 6: Monitoring and Maintenance

### 6.1 Set Up Bounce and Complaint Handling

1. Create SNS topics for bounces and complaints
2. Configure SES to send events to SNS topics
3. Set up Lambda functions or webhooks to process events
4. Remove bounced/complained emails from your mailing lists

### 6.2 Monitor Reputation

- Check SES console regularly for reputation metrics
- Investigate spikes in bounce/complaint rates
- Maintain consistent sending patterns
- Warm up new sending domains gradually

### 6.3 Rate Limiting

- Start with conservative sending rates (50/day)
- Gradually increase to 100 → 250 → 500 emails/day
- Monitor for throttling errors
- Implement exponential backoff in code

---

## Troubleshooting

### Domain Verification Fails

- Check DNS records are correctly added
- Wait for DNS propagation (up to 72 hours)
- Verify record names match exactly (including subdomain)
- Use `dig` or online DNS checker to verify records

### Emails Going to Spam

- Verify SPF, DKIM, and DMARC records are correct
- Check email content (avoid spam trigger words)
- Build sender reputation gradually
- Use consistent "From" address

### SES Throttling Errors

- Check current sending rate in SES console
- Implement rate limiting in application code
- Use exponential backoff for retries
- Request sending limit increase if needed

### Production Access Denied

- Ensure use case is clearly described
- Provide accurate sending volume estimates
- Demonstrate bounce/complaint handling process
- Re-apply with additional information if needed

---

## Additional Resources

- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [SES Best Practices](https://docs.aws.amazon.com/ses/latest/dg/best-practices.html)
- [Email Authentication Guide](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication.html)
- [SES Pricing](https://aws.amazon.com/ses/pricing/)

---

## Checklist

Before using SES in production:

- [ ] Domain verified in SES console
- [ ] SPF record added to DNS
- [ ] DKIM records (3 CNAME) added to DNS
- [ ] DMARC record added to DNS
- [ ] Production access requested and approved
- [ ] Test email sent successfully
- [ ] Email authentication verified (mail-tester.com score 8+/10)
- [ ] Environment variables configured
- [ ] IAM permissions set up (if using IAM)
- [ ] Bounce/complaint handling configured
- [ ] Monitoring dashboard set up

---

**Last Updated**: 2025-01-15  
**Maintained By**: DevOps Team

