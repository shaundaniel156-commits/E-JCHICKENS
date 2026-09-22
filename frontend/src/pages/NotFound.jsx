import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

import { Card, EmptyState } from '../components/ui'

export default function NotFound() {
  return (
    <Card style={{ maxWidth: 560, margin: '40px auto' }}>
      <EmptyState
        icon={Compass}
        title="That page does not exist"
        message="The link may be out of date, or the page may have been moved. Let's get you back to the dashboard."
        action={
          <Link to="/" className="btn">
            Back to the dashboard
          </Link>
        }
      />
    </Card>
  )
}
