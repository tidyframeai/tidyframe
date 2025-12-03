import { Link } from 'react-router-dom';
import { Checkbox } from '@/components/ui/checkbox';

interface ConsentCheckboxesProps {
  termsAccepted: boolean;
  onTermsAcceptedChange: (checked: boolean) => void;
  privacyAccepted: boolean;
  onPrivacyAcceptedChange: (checked: boolean) => void;
}

export default function ConsentCheckboxes({
  termsAccepted,
  onTermsAcceptedChange,
  privacyAccepted,
  onPrivacyAcceptedChange,
}: ConsentCheckboxesProps) {
  return (
    <div className="space-y-4">
      {/* Terms of Service - now includes all attestations in Article 2.4 */}
      <div className="flex items-start space-x-3 p-3 border rounded-lg">
        <Checkbox
          id="terms-acceptance"
          checked={termsAccepted}
          onCheckedChange={onTermsAcceptedChange}
          className="mt-0.5"
        />
        <label
          htmlFor="terms-acceptance"
          className="text-sm cursor-pointer leading-relaxed"
        >
          I agree to the{' '}
          <Link
            to="/legal/terms-of-service"
            className="text-primary underline font-medium"
            target="_blank"
            rel="noopener noreferrer"
          >
            Terms of Service
          </Link>
          {' '}(includes attestations: 18+ age, US location, and arbitration agreement)
        </label>
      </div>

      {/* Privacy Policy */}
      <div className="flex items-start space-x-3 p-3 border rounded-lg">
        <Checkbox
          id="privacy-acceptance"
          checked={privacyAccepted}
          onCheckedChange={onPrivacyAcceptedChange}
          className="mt-0.5"
        />
        <label
          htmlFor="privacy-acceptance"
          className="text-sm cursor-pointer leading-relaxed"
        >
          I agree to the{' '}
          <Link
            to="/legal/privacy-policy"
            className="text-primary underline font-medium"
            target="_blank"
            rel="noopener noreferrer"
          >
            Privacy Policy
          </Link>
        </label>
      </div>

      {/* Minimal legal notice */}
      <p className="text-[10px] text-muted-foreground/60 mt-4 leading-relaxed">
        By agreeing to the Terms of Service, you attest that you are at least 18 years old, located in the United States,
        and acknowledge the mandatory arbitration clause. All data processing is described in our Privacy Policy.
      </p>
    </div>
  );
}
