import { SpaLink } from './SpaLink'
import type { AppRoute } from './route'

type Doc = 'terms' | 'privacy'

type Props = {
  doc: Doc
}

const TITLES: Record<Doc, string> = {
  terms: 'Terms of Use',
  privacy: 'Privacy Policy',
}

const UPDATED = '30 July 2026'

export function LegalPage({ doc }: Props) {
  const other: AppRoute = doc === 'terms' ? 'privacy' : 'terms'
  const otherLabel = doc === 'terms' ? 'Privacy Policy' : 'Terms of Use'

  return (
    <div className="legal">
      <header className="legal-top">
        <SpaLink to="home" className="legal-back">
          Back to Brisbane Parking
        </SpaLink>
        <p className="legal-brand">Brisbane Parking</p>
        <h1 className="legal-title">{TITLES[doc]}</h1>
        <p className="legal-updated">Last updated {UPDATED}</p>
      </header>

      <main className="legal-body">
        {doc === 'terms' ? <TermsBody /> : <PrivacyBody />}
      </main>

      <footer className="legal-footer">
        <SpaLink to={other}>{otherLabel}</SpaLink>
        <span aria-hidden="true"> · </span>
        <SpaLink to="home">Map</SpaLink>
      </footer>
    </div>
  )
}

function TermsBody() {
  return (
    <>
      <p>
        Brisbane Parking Finder (“the App”) is an independent civic utility. It is not
        affiliated with, endorsed by, or operated by Brisbane City Council or any other
        government body.
      </p>

      <h2>Acceptance</h2>
      <p>
        By using the App you agree to these Terms of Use. If you do not agree, do not use
        the App.
      </p>

      <h2>What the App provides</h2>
      <p>
        The App shows map pins and estimates for paid street parking meters in Brisbane,
        including a current-hour “chance free” figure derived from historical occupancy
        forecasts and related open data. It is a planning aid only. It is not live bay
        sensing, not enforcement advice, and not a guarantee that a bay will be free or
        that parking is lawful at a given time or place.
      </p>

      <h2>Your responsibility</h2>
      <p>
        You alone are responsible for how you use and interpret the App, including any
        decision to drive, park, wait, or rely on a forecast, pin colour, chart, status,
        or other output.
      </p>
      <ul>
        <li>
          Always check signs, meters, clearways, operating hours, and local rules at the
          kerb before you park.
        </li>
        <li>
          Forecasts can be wrong, incomplete, outdated, or based on zone averages when
          meter-level data is missing.
        </li>
        <li>
          Parking fines, towing, traffic offences, time spent circling, fuel, and any
          other loss or inconvenience arising from your use or interpretation of the App
          are your responsibility.
        </li>
      </ul>
      <p>
        The operators of the App are not responsible for your parking decisions or for
        any reliance you place on the App’s information.
      </p>

      <h2>No warranties</h2>
      <p>
        The App is provided “as is” and “as available”, without warranties of any kind,
        whether express or implied, including accuracy, fitness for a particular purpose,
        availability, or non-infringement. Data may contain errors. Features may change or
        stop without notice.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the fullest extent permitted by law, the App’s authors, contributors, and
        operators are not liable for any claim, loss, damage, cost, or expense (including
        parking fines, consequential loss, or lost time) arising from or related to your
        use of the App, inability to use it, or reliance on its content. Where liability
        cannot be excluded, it is limited to re-supply of the service or the minimum
        amount required by applicable law.
      </p>

      <h2>Data and attribution</h2>
      <p>
        Parking meter and occupancy forecasting data are © Brisbane City Council and
        licensed under Creative Commons Attribution 4.0 International (CC BY 4.0). Map
        basemap tiles are provided by third parties (see the Privacy Policy). Source code
        is offered under the MIT License where published.
      </p>

      <h2>Acceptable use</h2>
      <p>
        Do not misuse the App, attempt to disrupt it, scrape it in a way that harms
        service availability, or use it for unlawful purposes. The App may rate-limit or
        refuse access where needed to keep the service usable.
      </p>

      <h2>Voluntary support</h2>
      <p>
        You may optionally buy a coffee (currently A$5) through Stripe checkout inside
        the App. That payment is a voluntary tip to support the project, not a purchase
        of parking advice, a subscription, or a guaranteed product.
      </p>
      <ul>
        <li>
          Card details are processed by Stripe under Stripe’s terms and privacy policy.
          We do not store card numbers.
        </li>
        <li>
          Supporters may receive early access to premium features when those features
          exist. Premium features are not available yet and may change, be delayed, or
          be withdrawn without notice.
        </li>
        <li>
          Tips are generally non-refundable unless required by law. If you believe a
          payment was made in error, contact us through the project repository before
          disputing with your bank.
        </li>
      </ul>
      <p>
        Paying does not change your parking responsibilities under these Terms. How we
        handle supporter payment data is described in the{' '}
        <SpaLink to="privacy">Privacy Policy</SpaLink>.
      </p>

      <h2>Changes</h2>
      <p>
        These terms may be updated from time to time. Continued use after an update means
        you accept the revised terms. The “Last updated” date at the top of this page
        will change when we revise them.
      </p>

      <h2>Governing law</h2>
      <p>
        These terms are governed by the laws of Queensland, Australia. Courts in that
        jurisdiction have non-exclusive jurisdiction, subject to any non-excludable
        consumer rights that apply to you.
      </p>

      <p className="legal-note">
        This page is a plain-language summary of how the App is offered. It is not legal
        advice.
      </p>
    </>
  )
}

function PrivacyBody() {
  return (
    <>
      <p>
        This Privacy Policy explains what limited information the Brisbane Parking Finder
        App handles when you use it in a browser.
      </p>

      <h2>Accounts and sign-in</h2>
      <p>
        You can browse the map without an account. After a short free trial of meter
        detail views, the App may ask you to sign in (for example with Google via Clerk)
        to open more meters. If you sign in, Clerk processes authentication on our behalf
        and we may receive a user id and email address associated with your account. We
        use that only to recognize signed-in sessions and do not sell it.
      </p>

      <h2>Information processed to run the App</h2>
      <ul>
        <li>
          <strong>Map and meter requests.</strong> When you view the map or open a meter,
          your browser requests data from the App’s API (for example viewport bounds,
          suburb filter, or a meter id). Servers typically see standard request metadata
          such as IP address, user agent, and time of request in ordinary web logs.
        </li>
        <li>
          <strong>Basemap tiles.</strong> Street map data is loaded from OpenFreeMap
          (OpenStreetMap data) servers. Those providers may process technical data (such as IP address
          and tile coordinates) under their own policies.
        </li>
        <li>
          <strong>Your location.</strong> If you allow it, your browser shares your position
          with the App to show you on the map and measure distance to a meter. It stays on
          your device and is not sent to our servers. When you tap Apple Maps or Google Maps
          for directions, your position and the meter location are passed to that provider.
        </li>
        <li>
          <strong>Local preferences.</strong> The App may store simple flags in your
          browser’s <code>localStorage</code> (for example a first-visit flag, and which
          meters you opened during the free trial). Those values stay on your device; they
          are not sent to us as a profile.
        </li>
        <li>
          <strong>Authentication (when you sign in).</strong> Sign-in is handled by Clerk.
          Clerk’s privacy policy applies to that service. We receive session-related
          identifiers needed to know you are signed in.
        </li>
        <li>
          <strong>Voluntary support payments.</strong> If you buy a coffee, checkout is
          handled by Stripe inside a dialog in the App. Card details go to Stripe and
          never reach our servers. Stripe then notifies our API that a payment
          succeeded, and we store the checkout id, amount, the email address Stripe
          collected, and your Clerk user id if you were signed in. We use those records
          only to recognize supporters and to honour supporter access.
        </li>
      </ul>

      <h2>Cookies and tracking</h2>
      <p>
        The App does not set advertising cookies and does not include third-party
        analytics or ad networks in its own code. Clerk may set cookies or similar
        storage needed for authentication sessions. When you open the supporter checkout
        dialog, Stripe may set cookies or similar storage needed to process payment.
        Stripe’s privacy policy applies to that checkout. Your browser or network may
        still apply their own logging.
      </p>

      <h2>How we use information</h2>
      <p>
        Technical request data, if retained on the API host, is used only to operate,
        secure, and debug the service (for example to understand load or fix errors). We
        do not sell personal information.
      </p>

      <h2>Retention</h2>
      <p>
        Browser <code>localStorage</code> remains until you clear site data. Server logs,
        if kept, are retained only as long as needed for operations and then discarded or
        rotated according to the host’s normal practice. Supporter payment records are
        kept for as long as supporter access is offered, or until you ask us to delete
        them; Stripe keeps its own transaction records under its policies.
      </p>

      <h2>Your choices</h2>
      <p>
        You can clear site data in your browser to remove local flags (including the free
        trial meter list). If you created a Clerk account, you can manage or delete it
        through the account menu or Clerk’s flows. If you paid as a supporter and want
        your payment record removed from our database, open an issue on the project
        repository with enough detail for us to find the payment (for example the email
        used at checkout). You can stop using the App at any time. Blocking third-party
        map tiles may limit map display.
      </p>

      <h2>Children</h2>
      <p>
        The App is a general parking utility and is not directed at children. Do not
        submit personal information about a child through any channel related to the App.
      </p>

      <h2>Changes</h2>
      <p>
        We may update this policy as the App evolves. The “Last updated” date at the top
        of this page will change when we revise it.
      </p>

      <h2>Contact</h2>
      <p>
        For privacy questions about this App, open an issue on the project’s public
        repository if one is linked from the site or source distribution.
      </p>

      <p className="legal-note">
        Forecast outputs are estimates. How you use them is covered in the{' '}
        <SpaLink to="terms">Terms of Use</SpaLink>.
      </p>
    </>
  )
}
