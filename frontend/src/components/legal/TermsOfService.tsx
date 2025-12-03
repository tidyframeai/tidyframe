import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'react-router-dom';

export default function TermsOfService() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Card>
        <CardHeader className="text-center">
          <div className="flex justify-center mb-6">
            <Link to="/">
              <img src="/logo-with-name.png" alt="TidyFrame" className="h-16" />
            </Link>
          </div>
          <CardTitle className="text-3xl font-bold mb-4">
            TERMS OF SERVICE AGREEMENT
          </CardTitle>
          <div className="text-xl text-muted-foreground">
            <p className="font-semibold">TidyFrame AI Data Processing Platform</p>
            <p>Last Updated: October 3, 2025</p>
            <p>Effective Date: August 2, 2025</p>
          </div>
        </CardHeader>

        <CardContent className="prose max-w-none">
          <p className="text-sm text-muted-foreground mb-8">
            This Terms of Service Agreement ("Agreement") is a legally binding contract between you ("Customer,"
            "you," or "your") and TidyFrame AI, LLC ("Company," "we," "us," or "our"). Please read it carefully.
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 1: DEFINITIONS AND INTERPRETATION</h2>

            <h3 className="text-xl font-semibold mb-3">1.1 Definitions</h3>
            <p className="mb-4">For purposes of this Agreement, the following terms shall have the meanings set forth below:</p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>"Agreement" or "Terms"</strong> means this Terms of Service Agreement, as it may be amended from time to time.</li>
              <li><strong>"Company," "we," "us," or "our"</strong> means TidyFrame AI, LLC, a Delaware limited liability company, with its principal place of business at 8 The Green STE B, Dover, DE 19901.</li>
              <li><strong>"Customer," "you," or "your"</strong> means the individual or entity accessing or using the Services.</li>
              <li><strong>"Platform"</strong> means the TidyFrame AI data processing platform accessible at tidyframe.com and any related applications, software, or services.</li>
              <li><strong>"Services"</strong> means the data processing, analysis, and related services provided through the Platform.</li>
              <li><strong>"User Content"</strong> means any data, files, information, or other content uploaded, submitted, or transmitted by you through the Platform.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">1.2 Interpretation</h3>
            <p className="mb-4">This Agreement shall be interpreted in accordance with the laws of the State of Delaware. Headings are for convenience only and do not affect interpretation.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 2: ACCEPTANCE AND SCOPE</h2>

            <h3 className="text-xl font-semibold mb-3">2.1 Binding Agreement</h3>
            <p className="mb-4">By accessing, browsing, or using the Platform, you acknowledge that you have read, understood, and agree to be bound by this Agreement and our Privacy Policy, which is incorporated herein by reference.</p>

            <h3 className="text-xl font-semibold mb-3">2.2 Capacity</h3>
            <p className="mb-4">You represent and warrant that: (a) you are at least 18 years of age; (b) you have the legal capacity to enter into this Agreement; and (c) if you are acting on behalf of an entity, you have the full authority to bind such entity to this Agreement.</p>

            <h3 className="text-xl font-semibold mb-3">2.3 Modifications</h3>
            <p className="mb-4">We reserve the right to modify this Agreement at any time by posting the revised terms on the Platform. We will notify you of material changes, which will become effective thirty (30) days after posting. Your continued use of the Services after the effective date constitutes your acceptance of the modifications.</p>

            <div className="bg-status-info-bg border border-status-info-border p-4 rounded-lg mb-4">
              <h3 className="text-xl font-semibold mb-3 text-status-info">2.4 User Attestations and Representations</h3>
              <p className="mb-4">
                By accepting these Terms of Service and creating an account, you explicitly confirm, attest, warrant, and represent that:
              </p>
              <ul className="list-disc pl-6 space-y-2 mb-4">
                <li>(a) You are at least eighteen (18) years of age and have full legal capacity to enter into this binding agreement;</li>
                <li>(b) You are physically located in the United States at the time of registration and will access and use the Services only from within the United States;</li>
                <li>(c) You have read, understood, and agree to be bound by the mandatory arbitration clause and class action waiver contained in Article 15;</li>
                <li>(d) All information provided during registration is accurate, complete, truthful, and current;</li>
                <li>(e) You will not use VPNs, proxy servers, or other technologies to mask your location or circumvent geographic restrictions;</li>
                <li>(f) You understand that providing false attestations or violating these representations may result in immediate account termination and potential legal action.</li>
              </ul>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 3: SERVICE DESCRIPTION AND AVAILABILITY</h2>

            <h3 className="text-xl font-semibold mb-3">3.1 Services Overview</h3>
            <p className="mb-4">The Platform provides automated data processing, cleaning, analysis, and transformation services for structured and unstructured datasets uploaded by customers.</p>

            <h3 className="text-xl font-semibold mb-3">3.2 Service Limitations</h3>
            <p className="mb-2">Our Services are subject to limitations, including but not limited to:</p>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) Processing capacity and file size limits as specified in your service plan;</li>
              <li>(b) Supported file formats and data types as documented on the Platform;</li>
              <li>(c) Geographic restrictions and compliance requirements;</li>
              <li>(d) Technical limitations inherent in automated processing systems.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">3.3 Service Availability</h3>
            <p className="mb-4">We will use commercially reasonable efforts to maintain high availability but do not guarantee uninterrupted service. We may suspend Services for maintenance, updates, or security measures. We will provide advance notice where practicable.</p>

            <h3 className="text-xl font-semibold mb-3">3.4 No Professional Advice</h3>
            <p className="mb-4">The Services provide data processing tools and outputs. They are not intended to be a substitute for professional, legal, financial, or medical advice. You are solely responsible for validating all outputs and seeking appropriate professional consultation.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 4: USER ACCOUNTS AND REGISTRATION</h2>

            <h3 className="text-xl font-semibold mb-3">4.1 Account Creation</h3>
            <p className="mb-4">To access the Services, you must create an account by providing accurate, complete, and current information. You are responsible for maintaining the confidentiality of your account credentials.</p>

            <h3 className="text-xl font-semibold mb-3">4.2 Account Security</h3>
            <p className="mb-2">You agree to: </p>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) use a strong, unique password;</li>
              <li>(b) notify us immediately of any unauthorized access to your account;</li>
              <li>(c) not share your account credentials; and</li>
              <li>(d) accept full responsibility for all activities that occur under your account.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">4.3 Account Suspension</h3>
            <p className="mb-4">We reserve the right to suspend or terminate your account if you violate this Agreement, engage in fraudulent activity, or pose a security risk to the Platform or other users, with or without prior notice.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 5: ACCEPTABLE USE POLICY</h2>

            <h3 className="text-xl font-semibold mb-3">5.1 Permitted Use</h3>
            <p className="mb-4">You may use the Services solely for lawful business and personal purposes in accordance with this Agreement and all applicable laws.</p>

            <h3 className="text-xl font-semibold mb-3">5.2 Prohibited Activities</h3>
            <p className="mb-2">You shall not:</p>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) Upload, process, or transmit any unlawful, harmful, defamatory, obscene, or otherwise objectionable content;</li>
              <li>(b) Violate any applicable laws, regulations, or third-party rights, including privacy and intellectual property rights;</li>
              <li>(c) Upload malware, viruses, or any other malicious code;</li>
              <li>(d) Attempt to gain unauthorized access to our systems, networks, or other users' accounts;</li>
              <li>(e) Reverse engineer, decompile, or attempt to derive the source code of the Platform;</li>
              <li>(f) Use automated tools to scrape, harvest, or collect data from the Platform without our express written permission;</li>
              <li>(g) Interfere with or disrupt the Platform's functionality, security, or integrity;</li>
              <li>(h) Impersonate any person or entity or misrepresent your affiliation with any person or entity;</li>
              <li>(i) Use the Services for competitive analysis or to develop a competing product;</li>
              <li>(j) Process the personal data of others without a proper legal basis and authorization.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">5.3 Content Monitoring</h3>
            <p className="mb-4">We reserve the right, but have no obligation, to monitor, review, or remove any User Content that, in our sole discretion, violates this Agreement.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 6: PAYMENT TERMS AND BILLING</h2>

            <h3 className="text-xl font-semibold mb-3">6.1 Service Plans</h3>
            <p className="mb-4">Services are provided on a subscription or pay-per-use basis according to the pricing plans displayed on the Platform at the time of purchase.</p>

            <h3 className="text-xl font-semibold mb-3">6.2 Payment Processing</h3>
            <p className="mb-4">Payments are processed through third-party payment processors, such as Stripe, Inc. By providing your payment information, you authorize us and our payment processor to charge all applicable fees to your selected payment method.</p>

            <h3 className="text-xl font-semibold mb-3">6.3 Billing and Invoicing</h3>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) Subscription fees are billed in advance on a recurring basis (e.g., monthly or annually).</li>
              <li>(b) Usage-based fees are billed monthly in arrears.</li>
              <li>(c) All fees are non-refundable except as expressly provided in this Agreement.</li>
              <li>(d) Prices are subject to change with thirty (30) days' notice.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">6.4 Late Payment</h3>
            <p className="mb-4">Overdue accounts may be suspended without notice. We may charge late fees of 1.5% per month on the outstanding balance or the maximum rate permitted by law, whichever is less.</p>

            <h3 className="text-xl font-semibold mb-3">6.5 Taxes</h3>
            <p className="mb-4">You are responsible for all applicable taxes, duties, and governmental assessments (excluding taxes based on our net income) related to your use of the Services.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 7: REFUND AND CANCELLATION POLICY</h2>

            <h3 className="text-xl font-semibold mb-3">7.1 Refund Eligibility</h3>
            <p className="mb-2">Refunds may be issued at our sole discretion, and are generally limited to:</p>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) Technical failures originating from our Platform that prevent service delivery for more than 48 consecutive hours;</li>
              <li>(b) Confirmed billing errors on our part.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">7.2 Refund Process</h3>
            <p className="mb-4">Refund requests must be submitted in writing within thirty (30) days of the billing date with documentation supporting the claim. Approved refunds will be processed within ten (10) business days.</p>

            <h3 className="text-xl font-semibold mb-3">7.3 Chargeback Policy</h3>
            <p className="mb-4">Initiating a chargeback without first contacting us to resolve the issue may result in immediate account suspension and collection of associated fees and costs.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 8: INTELLECTUAL PROPERTY RIGHTS</h2>

            <h3 className="text-xl font-semibold mb-3">8.1 Platform Ownership</h3>
            <p className="mb-4">We own all rights, title, and interest in and to the Platform, including all software, algorithms, designs, trademarks, copyrights, trade secrets, and other proprietary technologies.</p>

            <h3 className="text-xl font-semibold mb-3">8.2 User Content Rights</h3>
            <p className="mb-4">You retain all ownership rights to your User Content. You grant us a limited, non-exclusive, worldwide, royalty-free license to access, use, process, store, and transmit your User Content solely as necessary to provide the Services to you.</p>

            <h3 className="text-xl font-semibold mb-3">8.3 Service Outputs</h3>
            <p className="mb-4">You own the specific outputs generated from your User Content through the Services. However, our underlying processing methods, algorithms, and any anonymized, aggregated data derived from the use of the Services remain our intellectual property.</p>

            <h3 className="text-xl font-semibold mb-3">8.4 Feedback License</h3>
            <p className="mb-4">If you provide any feedback, suggestions, or improvements regarding the Services, you grant us an unrestricted, perpetual, irrevocable, royalty-free license to use and incorporate such feedback into our Services without any obligation or compensation to you.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 9: PRIVACY AND DATA PROTECTION</h2>

            <h3 className="text-xl font-semibold mb-3">9.1 Privacy Policy</h3>
            <p className="mb-4">Our collection, use, and protection of personal information is governed by our Privacy Policy, which is incorporated by reference and forms an integral part of this Agreement.</p>

            <h3 className="text-xl font-semibold mb-3">9.2 Data Security</h3>
            <p className="mb-4">We implement and maintain industry-standard administrative, physical, and technical security measures to protect User Content from unauthorized access, use, or disclosure.</p>

            <h3 className="text-xl font-semibold mb-3">9.3 Data Retention</h3>
            <p className="mb-4">User Content is retained only as long as necessary to provide the Services and comply with our legal obligations, as further described in our Privacy Policy.</p>

            <h3 className="text-xl font-semibold mb-3">9.4 Use of Third-Party Services</h3>
            <p className="mb-4">Our Services may incorporate third-party artificial intelligence and data processing tools, including but not limited to the Google Gemini API ("Third-Party AI Providers"). These providers may process the information you submit to deliver outputs and insights. By using our Services, you acknowledge and agree that:</p>
            <ul className="list-disc pl-6 space-y-1 mb-4">
              <li>(a) Certain data you provide may be transmitted to and processed by Third-Party AI Providers in order to deliver the features and functionality of our Services.</li>
              <li>(b) We do not control the operation, accuracy, or availability of Third-Party AI Providers and are not responsible for any errors, omissions, or interruptions that may result from their services.</li>
              <li>(c) You agree not to submit content that violates applicable laws, regulations, or the acceptable use policies of our Third-Party AI Providers (including Google's policies).</li>
              <li>(d) We reserve the right to suspend or terminate your access to our Services if your use of the Services causes us to be in violation of Third-Party AI Provider terms.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">9.5 Compliance</h3>
            <p className="mb-4">We comply with applicable U.S. data protection laws, including the California Consumer Privacy Act (CCPA) and other state privacy laws, as detailed in our Privacy Policy.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 10: GEOGRAPHIC RESTRICTIONS</h2>

            <div className="bg-status-error-bg border border-status-error-border p-4 rounded-lg mb-4">
              <h3 className="text-xl font-semibold mb-3 text-status-error">10.1 U.S. Services Only</h3>
              <p className="mb-2 text-status-error">The Services are intended solely for individuals and entities located within the United States and are provided in compliance with applicable U.S. laws and regulations. We do not knowingly market, offer, or provide Services to users outside the United States. Any access to or use of the Services from outside the United States is unauthorized and at the user's own risk.</p>
            </div>

            <h3 className="text-xl font-semibold mb-3">10.2 No Liability for International Use</h3>
            <p className="mb-4">TidyFrame AI expressly disclaims any liability for access to or use of the Services by individuals or entities located outside the United States. Users who choose to access the Services from other jurisdictions do so voluntarily and are solely responsible for compliance with local laws. We make no representations or warranties that the Services are appropriate or available for use in any location outside the United States.</p>

            <h3 className="text-xl font-semibold mb-3">10.3 Enforcement</h3>
            <p className="mb-4">We reserve the right to restrict or terminate access to the Services for any user we believe to be located outside the United States or in violation of this Article, without notice and at our sole discretion.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 11: WARRANTIES AND DISCLAIMERS</h2>

            <h3 className="text-xl font-semibold mb-3">11.1 Limited Warranty</h3>
            <p className="mb-4">We warrant that the Services will perform substantially in accordance with our official documentation under normal use.</p>

            <h3 className="text-xl font-semibold mb-3">11.2 DISCLAIMER OF WARRANTIES</h3>
            <p className="mb-4">EXCEPT AS EXPRESSLY SET FORTH HEREIN, THE SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE." WE DISCLAIM ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.</p>

            <h3 className="text-xl font-semibold mb-3">11.3 No Guarantee of Results</h3>
            <p className="mb-4">We do not guarantee the accuracy, completeness, or reliability of any Service outputs. You are solely responsible for reviewing and validating all results before use or reliance.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 12: LIMITATION OF LIABILITY</h2>

            <h3 className="text-xl font-semibold mb-3">12.1 Liability Cap</h3>
            <p className="mb-4">TO THE MAXIMUM EXTENT PERMITTED BY LAW, OUR TOTAL AGGREGATE LIABILITY TO YOU FOR ANY AND ALL CLAIMS ARISING OUT OF OR RELATING TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, SHALL NOT EXCEED THE TOTAL AMOUNT OF FEES PAID BY YOU TO US IN THE TWELVE (12) MONTHS IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO THE CLAIM.</p>

            <h3 className="text-xl font-semibold mb-3">12.2 Exclusion of Consequential Damages</h3>
            <p className="mb-4">IN NO EVENT SHALL WE BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, PUNITIVE, OR EXEMPLARY DAMAGES, INCLUDING BUT NOT LIMITED TO DAMAGES FOR LOSS OF PROFITS, REVENUE, DATA, OR GOODWILL, EVEN IF WE HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.</p>

            <h3 className="text-xl font-semibold mb-3">12.3 Basis of the Bargain</h3>
            <p className="mb-4">The limitations of liability set forth in this Article are fundamental elements of the basis of the bargain between you and us.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 13: INDEMNIFICATION</h2>

            <h3 className="text-xl font-semibold mb-3">13.1 User Indemnification</h3>
            <p className="mb-4">You agree to indemnify, defend, and hold harmless the Company, its officers, directors, employees, and agents from and against any claims, liabilities, damages, losses, and expenses (including reasonable attorneys' fees) arising out of or in any way connected with: (a) your use of the Services; (b) your User Content; (c) your violation of this Agreement; or (d) your violation of any applicable law or any rights of a third party.</p>

            <h3 className="text-xl font-semibold mb-3">13.2 Defense Rights</h3>
            <p className="mb-4">We reserve the right, at your expense, to assume the exclusive defense and control of any matter for which you are required to indemnify us, and you agree to cooperate with our defense of these claims.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 14: TERMINATION</h2>

            <h3 className="text-xl font-semibold mb-3">14.1 Termination for Convenience</h3>
            <p className="mb-4">You may terminate this Agreement at any time by closing your account. We may terminate this Agreement at any time by providing you with thirty (30) days' written notice.</p>

            <h3 className="text-xl font-semibold mb-3">14.2 Termination for Cause</h3>
            <p className="mb-4">We may terminate this Agreement immediately upon notice if: (a) you materially breach this Agreement; (b) your account is subject to legal proceedings such as bankruptcy; or (c) your conduct is fraudulent, harmful, or violates applicable law.</p>

            <h3 className="text-xl font-semibold mb-3">14.3 Effect of Termination</h3>
            <p className="mb-4">Upon termination: (a) your right to access the Services will cease immediately; (b) all unpaid fees will become immediately due and payable; and (c) we will delete your User Content in accordance with our data retention policies. Provisions intended to survive termination (including Articles 8, 12, 13, and 15) shall remain in effect.</p>

            <h3 className="text-xl font-semibold mb-3">14.4 Data Export</h3>
            <p className="mb-4">You are responsible for exporting your User Content prior to termination. We are not obligated to maintain or provide access to your User Content after the termination date.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 15: DISPUTE RESOLUTION</h2>

            <h3 className="text-xl font-semibold mb-3">15.1 Governing Law</h3>
            <p className="mb-4">This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law principles.</p>

            <h3 className="text-xl font-semibold mb-3">15.2 Jurisdiction and Venue</h3>
            <p className="mb-4">Any legal action arising under this Agreement shall be brought exclusively in the state or federal courts located in New Castle County, Delaware, and you hereby consent to the personal jurisdiction and venue of such courts.</p>

            <div className="bg-status-info-bg border border-status-info-border p-4 rounded-lg mb-4">
              <h3 className="text-xl font-semibold mb-3 text-status-info">15.3 Mandatory Arbitration</h3>
              <p className="mb-2 text-status-info">Except for claims seeking injunctive relief, all disputes arising out of this Agreement shall be resolved through binding arbitration administered by the American Arbitration Association under its Commercial Arbitration Rules. The arbitration shall take place in New Castle County, Delaware.</p>
            </div>

            <div className="bg-status-info-bg border border-status-info-border p-4 rounded-lg mb-4">
              <h3 className="text-xl font-semibold mb-3 text-status-info">15.4 Class Action Waiver</h3>
              <p className="mb-2 text-status-info font-semibold">YOU AND THE COMPANY AGREE THAT ANY PROCEEDING, WHETHER IN ARBITRATION OR IN COURT, WILL BE CONDUCTED ONLY ON AN INDIVIDUAL BASIS AND NOT IN A CLASS, CONSOLIDATED, OR REPRESENTATIVE ACTION.</p>
            </div>

            <h3 className="text-xl font-semibold mb-3">15.5 Informal Resolution</h3>
            <p className="mb-4">Before initiating formal proceedings, the parties agree to first attempt to resolve the dispute informally through direct negotiation for a period of at least sixty (60) days.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 16: FORCE MAJEURE</h2>

            <h3 className="text-xl font-semibold mb-3">16.1 Excused Performance</h3>
            <p className="mb-4">Neither party shall be liable for any failure or delay in performance due to circumstances beyond its reasonable control, including acts of God, natural disasters, war, terrorism, labor disputes, government actions, or widespread internet outages.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 17: GENERAL PROVISIONS</h2>

            <h3 className="text-xl font-semibold mb-3">17.1 Entire Agreement</h3>
            <p className="mb-4">This Agreement, together with our Privacy Policy, constitutes the entire agreement between the parties and supersedes all prior communications.</p>

            <h3 className="text-xl font-semibold mb-3">17.2 Severability</h3>
            <p className="mb-4">If any provision of this Agreement is found to be invalid or unenforceable, the remaining provisions shall remain in full force and effect.</p>

            <h3 className="text-xl font-semibold mb-3">17.3 Assignment</h3>
            <p className="mb-4">You may not assign this Agreement without our prior written consent. We may assign this Agreement without restriction in connection with a merger, acquisition, or sale of all or substantially all of our assets.</p>

            <h3 className="text-xl font-semibold mb-3">17.4 Waiver</h3>
            <p className="mb-4">No waiver of any term shall be effective unless in writing.</p>

            <h3 className="text-xl font-semibold mb-3">17.5 Independent Contractors</h3>
            <p className="mb-4">The parties are independent contractors. This Agreement does not create any partnership, joint venture, or agency relationship.</p>

            <h3 className="text-xl font-semibold mb-3">17.6 Survival</h3>
            <p className="mb-4">Provisions that by their nature should survive termination shall survive, including those related to intellectual property, liability, indemnification, and dispute resolution.</p>

            <h3 className="text-xl font-semibold mb-3">17.7 Electronic Communications</h3>
            <p className="mb-4">You consent to receive communications from us electronically and agree that such communications satisfy any legal requirement for written notice.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">ARTICLE 18: CONTACT INFORMATION AND LEGAL NOTICES</h2>

            <h3 className="text-xl font-semibold mb-3">18.1 Company Contact Information</h3>
            <div className="bg-gray-50 p-4 rounded-lg mb-4">
              <p><strong>TidyFrame AI, LLC</strong></p>
              <p>8 The Green STE B, Dover, DE 19901</p>
              <p>United States</p>
              <p>Email: tidyframeai@gmail.com</p>
            </div>

            <h3 className="text-xl font-semibold mb-3">18.2 Legal Notices</h3>
            <p className="mb-4">All legal notices must be delivered in writing to the address specified above and will be deemed effective upon receipt.</p>

            <h3 className="text-xl font-semibold mb-3">18.3 Customer Support</h3>
            <p className="mb-4">For technical support and general inquiries, please contact us at tidyframeai@gmail.com. Our support hours are 9:00 AM to 5:00 PM Pacific Time, Monday through Friday. We aim to provide an initial response to support inquiries within one (1) business day.</p>
          </section>

          <div className="mt-12 pt-8 border-t">
            <p className="text-center font-semibold text-xl">
              BY USING THE SERVICES, YOU ACKNOWLEDGE THAT YOU HAVE READ, UNDERSTOOD, AND AGREE TO BE BOUND BY THIS AGREEMENT.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
