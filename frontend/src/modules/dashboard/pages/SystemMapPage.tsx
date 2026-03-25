import { useCallback, useEffect } from "react"
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import dagre from "dagre"
import { useQuery } from "@tanstack/react-query"
import { useNavigate, useLocation } from "react-router-dom"
import { Loader2, AlertCircle } from "lucide-react"

import { systemMapService } from "@/services/system-map.service"
import { SystemModuleNode } from "../components/SystemModuleNode"
import { PageHeader } from "@/components/layout/PageHeader"

const nodeTypes: any = {
  systemModule: SystemModuleNode,
}

const nodeWidth = 240
const nodeHeight = 80

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = "TB") => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    }
  })

  return { nodes: newNodes, edges }
}

export default function SystemMapPage() {
  const navigate = useNavigate()
  const location = useLocation()
  
  const { data, isLoading, error } = useQuery({
    queryKey: ["system-map"],
    queryFn: systemMapService.getSystemMap,
  })

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  useEffect(() => {
    if (data) {
      const initialNodes: Node[] = data.modules.map((mod) => ({
        id: mod.id,
        type: "systemModule",
        position: { x: 0, y: 0 }, // computed by dagre later
        data: { 
          ...mod,
          // Highlight if current browser path starts with this module's route
          isCurrent: location.pathname.startsWith(mod.route)
        },
      }))

      const initialEdges: Edge[] = data.connections.map((conn) => ({
        id: `${conn.source}-${conn.target}`,
        source: conn.source,
        target: conn.target,
        animated: true,
        style: { stroke: "hsl(var(--primary))", strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "hsl(var(--primary))",
        },
      }))

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        initialNodes,
        initialEdges,
        "TB" // Top to bottom layout
      )

      setNodes(layoutedNodes)
      setEdges(layoutedEdges)
    }
  }, [data, location.pathname, setNodes, setEdges])

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      // Navigate to the module's route when clicked
      if (node.data.route) {
        navigate((node.data as any).route)
      }
    },
    [navigate]
  )

  if (isLoading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center p-8 text-center bg-muted/20 border border-dashed rounded-xl">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Mapping system modules...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center p-8 text-center bg-destructive/10 rounded-xl">
        <AlertCircle className="w-8 h-8 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-destructive mb-2">Failed to load system map</h2>
        <p className="text-muted-foreground">Unable to fetch the module architecture.</p>
      </div>
    )
  }

  return (
    <div className="w-full flex flex-col h-[calc(100vh-8rem)]">
      <PageHeader 
        title="System Map" 
        description="Dynamic architectural blueprint of active ERP modules and their relationships."
      />
      
      <div className="flex-1 w-full mt-4 rounded-xl border bg-background shadow-sm overflow-hidden relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.5}
          maxZoom={1.5}
        >
          <Background color="#ccc" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
