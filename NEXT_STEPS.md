# Next Steps: AI Band Manager

## Milestone: Automated Email Outreach

**Goal:**
- Enable the system to scan for contact emails and send gig inquiry emails to venues, but only after confirming with the band.

**Tasks:**

- [ ] Implement email scanning and extraction for each gig opportunity.
- [ ] Integrate an email sending module (e.g., SMTP, Gmail API, or Outlook API).
- [ ] Add a band member confirmation step before sending an email:
    - Notify band members (e.g., via email or group chat) about a potential gig.
    - Wait for approval/confirmation from all or a majority of members.
    - Only send the gig inquiry email to the venue if approved.
- [ ] Log all outreach attempts and responses for tracking.

**Notes:**
- Consider privacy and rate limits when sending emails.
- Use templates for professional, personalized outreach.
- Optionally, add a UI or dashboard for band approval and tracking.

---

*This MR file documents the next development milestone and should be updated as progress is made.*
