import { LibraryPageHeader } from '../components/lobby/LibraryPageHeader'
import { StrategyLibraryEditor } from '../components/lobby/StrategyLibraryEditor'

export default function StrategyLibraryPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <LibraryPageHeader title="策略库" subtitle="按身份的策略模板" />
      <StrategyLibraryEditor />
    </div>
  )
}
