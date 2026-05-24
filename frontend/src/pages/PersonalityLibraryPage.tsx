import { LibraryPageHeader } from '../components/lobby/LibraryPageHeader'
import { PersonalityLibraryEditor } from '../components/lobby/PersonalityLibraryEditor'

export default function PersonalityLibraryPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <LibraryPageHeader title="人格库" subtitle="AI 人格模板" />
      <PersonalityLibraryEditor />
    </div>
  )
}
