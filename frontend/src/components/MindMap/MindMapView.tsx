/**
 * 思维导图组件
 */

import { useMemo, useRef, useEffect, useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  NodeTypes,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useNewsStore } from '@/stores'

// 自定义节点组件
function MindMapNode({ data }: { data: { label: string; color?: string; fontSize?: number } }) {
  return (
    <div
      className="px-4 py-2 rounded-lg shadow-md border-2 min-w-[120px] text-center"
      style={{
        backgroundColor: data.color || '#6366F1',
        borderColor: data.color || '#6366F1',
        fontSize: data.fontSize || 14,
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-white !w-2 !h-2" />
      <span className="text-white font-medium">{data.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-white !w-2 !h-2" />
    </div>
  )
}

const nodeTypes: NodeTypes = {
  mindmapNode: MindMapNode,
}

// 内部组件 - 必须在 ReactFlowProvider 内部使用 hooks
function MindMapViewInner() {
  const { currentMindmap, selectedNews, isLoadingMindmap } = useNewsStore()
  const wrapperRef = useRef<HTMLDivElement>(null)
  const { fitView } = useReactFlow()

  // 将思维导图数据转换为 ReactFlow 格式
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!currentMindmap) {
      return { initialNodes: [], initialEdges: [] }
    }

    const nodes: Node[] = []
    const edges: Edge[] = []

    const levelWidth = 280
    const nodeHeight = 60
    const verticalGap = 20
    const startX = 50
    const startY = 100
    const groupGap = 60  // 不同分支组之间的额外间距

    // 调试：打印接收到的树结构
    function debugNode(n: typeof currentMindmap.root, depth: number) {
      const indent = '  '.repeat(depth)
      console.log(`${indent}[MindMap] id=${n.id}, text="${n.text}", level=${n.level}, children=${n.children?.length || 0}`)
      n.children?.forEach(c => debugNode(c, depth + 1))
    }
    console.log('[MindMap] --- 接收到的思维导图树结构 ---')
    debugNode(currentMindmap.root, 0)

    // ====== 第一遍：计算每个节点的子树叶子节点数量（用于分配垂直空间）======
    function countLeaves(node: typeof currentMindmap.root): number {
      if (!node.children || node.children.length === 0) return 1
      let total = 0
      node.children.forEach(child => { total += countLeaves(child) })
      return total
    }

    // 缓存叶子节点计数
    const leafCache = new Map<string, number>()
    function getLeafCount(node: typeof currentMindmap.root): number {
      if (leafCache.has(node.id)) return leafCache.get(node.id)!
      const count = countLeaves(node)
      leafCache.set(node.id, count)
      return count
    }

    // ====== 为每个节点对象分配唯一的布局键（用对象引用，杜绝 ID 碰撞）======
    let layoutKeyCounter = 0
    const nodeRefToLayoutKey = new Map<any, string>()

    function getLayoutKey(node: any): string {
      if (!nodeRefToLayoutKey.has(node)) {
        nodeRefToLayoutKey.set(node, `k${++layoutKeyCounter}`)
      }
      return nodeRefToLayoutKey.get(node)!
    }

    // ====== 两遍布局算法 ======
    // 阶段1：为所有叶子层节点分配 Y 坐标
    const leafPositions = new Map<string, { x: number; y: number }>()
    const parentChildrenYRanges = new Map<string, { minY: number; maxY: number }>()

    function assignLeafPositions(
      node: typeof currentMindmap.root,
      level: number,
      currentY: number
    ): number {
      const x = startX + level * levelWidth
      const key = getLayoutKey(node)

      if (!node.children || node.children.length === 0) {
        // 叶子节点：分配当前位置
        leafPositions.set(key, { x, y: currentY })
        parentChildrenYRanges.set(key, { minY: currentY, maxY: currentY })
        console.log(`[MindMap] 叶子布局: key=${key}, id=${node.id}, text="${node.text}", pos=(${x}, ${currentY})`)
        return currentY + nodeHeight + verticalGap
      }

      // 分支节点：递归处理子节点
      let y = currentY

      node.children.forEach((child, idx) => {
        // 不同分支组之间加额外间距
        if (idx > 0) {
          y += groupGap
        }
        y = assignLeafPositions(child, level + 1, y)
      })

      // 汇总子节点的 Y 范围
      if (node.children.length > 0) {
        let minY = Infinity, maxY = -Infinity
        node.children.forEach(child => {
          const cKey = getLayoutKey(child)
          const range = parentChildrenYRanges.get(cKey)
          if (range) {
            minY = Math.min(minY, range.minY)
            maxY = Math.max(maxY, range.maxY)
          }
        })
        parentChildrenYRanges.set(key, { minY, maxY })
        console.log(`[MindMap] 分支布局: key=${key}, id=${node.id}, text="${node.text}", childrenY=[${minY}, ${maxY}]`)
      }

      return y
    }

    // 阶段2：设置所有节点的最终位置（父节点居中于子节点）
    function assignFinalPositions(node: typeof currentMindmap.root, parentLayoutKey?: string) {
      const x = startX + node.level * levelWidth
      const key = getLayoutKey(node)

      let y: number
      const range = parentChildrenYRanges.get(key)
      if (range) {
        // 父节点垂直居中于其子节点范围
        y = (range.minY + range.maxY) / 2
      } else {
        // 叶子节点使用之前计算的位置
        const leafPos = leafPositions.get(key)
        y = leafPos ? leafPos.y : startY
      }

      console.log(`[MindMap] 最终节点: key=${key}, id=${node.id}, text="${node.text}", finalPos=(${x}, ${y})`)

      // 使用 layoutKey 作为 ReactFlow 节点 ID（保证唯一性）
      nodes.push({
        id: key,
        type: 'mindmapNode',
        position: { x, y },
        data: {
          label: node.text,
          color: node.color,
          fontSize: node.font_size || 14,
        },
      })

      if (parentLayoutKey) {
        edges.push({
          id: `${parentLayoutKey}-${key}`,
          source: parentLayoutKey,
          target: key,
          type: 'smoothstep',
          style: { stroke: '#94a3b8', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#94a3b8',
          },
        })
      }

      node.children.forEach(child => {
        assignFinalPositions(child, key)
      })
    }

    if (currentMindmap.root) {
      assignLeafPositions(currentMindmap.root, 0, startY)
      assignFinalPositions(currentMindmap.root)
    }

    console.log(`[MindMap] 总计生成 ${nodes.length} 个节点, ${edges.length} 条连线`)
    return { initialNodes: nodes, initialEdges: edges }
  }, [currentMindmap])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // 当思维导图数据更新时更新节点，并触发 fitView
  useEffect(() => {
    if (currentMindmap && initialNodes.length > 0) {
      setNodes(initialNodes)
      setEdges(initialEdges)
      // 延迟执行 fitView 以确保节点已渲染
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 300 })
        console.log(`[MindMap] fitView 已触发，当前节点数: ${initialNodes.length}`)
      }, 100)
    }
  }, [currentMindmap, initialNodes, initialEdges, setNodes, setEdges, fitView])

  // 空状态
  if (!selectedNews) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-gray-50">
        <div className="w-20 h-20 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
          <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">选择新闻查看思维导图</h3>
        <p className="text-sm text-gray-500 max-w-sm">
          从左侧列表选择一条新闻，系统将自动生成对应的思维导图，帮助你更好地理解新闻内容
        </p>
      </div>
    )
  }

  // 加载状态
  if (isLoadingMindmap) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="w-16 h-16 rounded-full bg-primary-50 flex items-center justify-center mb-4">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">正在生成思维导图</h3>
        <p className="text-sm text-gray-500">
          分析 "{selectedNews.title.slice(0, 30)}..." 中的内容结构
        </p>
      </div>
    )
  }

  // 思维导图视图
  return (
    <div ref={wrapperRef} className="h-full w-full flex flex-col bg-gray-50">
      {/* 思维导图头部 */}
      <div className="px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-gray-900">思维导图</h3>
            <p className="text-xs text-gray-500">
              共 {currentMindmap?.total_nodes || 0} 个节点 · {currentMindmap?.layout || 'radial'} 布局
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-1 text-xs bg-primary-50 text-primary-600 rounded-full">
              {selectedNews.category}
            </span>
          </div>
        </div>
      </div>

      {/* 思维导图画布 */}
      <div className="flex-1 w-full" style={{ minHeight: '300px' }}>
        {currentMindmap && nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.1}
            maxZoom={2}
            attributionPosition="bottom-left"
          >
            <Background color="#e5e7eb" gap={20} />
            <Controls />
          </ReactFlow>
        ) : (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-500">无法生成思维导图</p>
          </div>
        )}
      </div>
    </div>
  )
}

// 导出组件 - 包裹 ReactFlowProvider
export function MindMapView() {
  return (
    <ReactFlowProvider>
      <MindMapViewInner />
    </ReactFlowProvider>
  )
}
