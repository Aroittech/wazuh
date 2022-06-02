#ifndef _ENVIRONMENT_H
#define _ENVIRONMENT_H

#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include <fmt/format.h>

#include <_builder/asset.hpp>
#include <_builder/expression.hpp>
#include <_builder/graph.hpp>
#include <_builder/json.hpp>
#include <_builder/registry.hpp>

constexpr const char* const DECODERS = "decoders";
constexpr const char* const RULES = "rules";
constexpr const char* const OUTPUTS = "outputs";
constexpr const char* const FILTERS = "filters";

static Asset::Type getAssetType(const std::string& name)
{
    if (name == DECODERS)
    {
        return Asset::Type::DECODER;
    }
    else if (name == RULES)
    {
        return Asset::Type::RULE;
    }
    else if (name == OUTPUTS)
    {
        return Asset::Type::OUTPUT;
    }
    else if (name == FILTERS)
    {
        return Asset::Type::FILTER;
    }
    else
    {
        throw std::runtime_error("Unknown asset type");
    }
}

class Environment
{
private:
    std::string m_name;
    std::unordered_map<std::string, std::shared_ptr<Asset>> m_assets;
    std::map<std::string, Graph<std::string, std::shared_ptr<Asset>>> m_graphs;

    void
    buildGraph(const std::unordered_map<std::string, Json>& assetsDefinitons,
               const std::string& graphName,
               Asset::Type type)
    {
        auto& graph = m_graphs[graphName];
        for (auto& [name, json] : assetsDefinitons)
        {
            auto asset = std::make_shared<Asset>(json, type);
            m_assets.insert(std::make_pair(name, asset));
            graph.addNode(name, asset);
            if (asset->m_parents.empty())
            {
                graph.addEdge(graph.root(), name);
            }
            else
            {
                for (auto& parent : asset->m_parents)
                {
                    graph.addEdge(parent, name);
                }
            }
        }
    }

    void addFilters(const std::string& graphName)
    {
        auto& graph = m_graphs[graphName];
        for (auto& [name, asset] : m_assets)
        {
            if (asset->m_type == Asset::Type::FILTER)
            {
                for (auto& parent : asset->m_parents)
                {
                    if (graph.hasNode(parent))
                    {
                        graph.node(parent)->m_filters.insert(name);
                    }
                }
            }
        }
    }

public:
    Environment() = default;
    template<typename T>
    Environment(std::string name, const Json& jsonDefinition, T catalog)
        : m_name {name}
    {
        auto envObj = jsonDefinition.getObject();

        // Filters are not graphs, its treated as a special case.
        // We just add them to the asset map and then inject them into each
        // graph.
        auto filtersPos = std::find_if(
            envObj.begin(),
            envObj.end(),
            [](auto& tuple) { return std::get<0>(tuple) == FILTERS; });
        if (filtersPos != envObj.end())
        {
            auto filtersList = std::get<1>(*filtersPos).getArray();
            std::transform(
                filtersList.begin(),
                filtersList.end(),
                std::inserter(m_assets, m_assets.begin()),
                [&](auto& json)
                {
                    return std::make_pair(
                        json.getString(),
                        std::make_shared<Asset>(
                            catalog.getAsset(1, std::string(json.getString())),
                            Asset::Type::FILTER));
                });
            envObj.erase(filtersPos);
        }

        // Build graphs
        for (auto& [name, json] : envObj)
        {
            auto assetNames = json.getArray();

            m_graphs.insert(
                std::make_pair<std::string,
                               Graph<std::string, std::shared_ptr<Asset>>>(
                    std::string {name},
                    {std::string(name + "Input"),
                     std::make_shared<Asset>(name + "Input",
                                             getAssetType(name))}));

            // Obtain assets jsons
            auto assetsDefinitions = std::unordered_map<std::string, Json>();
            std::transform(
                assetNames.begin(),
                assetNames.end(),
                std::inserter(assetsDefinitions, assetsDefinitions.begin()),
                [&](auto& json)
                {
                    return std::make_pair(
                        json.getString(),
                        catalog.getAsset(static_cast<int>(getAssetType(name)),
                                         std::string(json.getString())));
                });

            // Build graph
            buildGraph(assetsDefinitions, name, getAssetType(name));

            // Add filters
            addFilters(name);
        }
    }

    std::string name() const
    {
        return m_name;
    }

    std::unordered_map<std::string, std::shared_ptr<Asset>>& assets()
    {
        return m_assets;
    }

    std::string getGraphivzStr()
    {
        std::stringstream ss;
        ss << "digraph G {" << std::endl;
        ss << "compound=true;" << std::endl;
        ss << fmt::format("fontname=\"Helvetica,Arial,sans-serif\";")
           << std::endl;
        ss << fmt::format("fontsize=12;") << std::endl;
        ss << fmt::format("node [fontname=\"Helvetica,Arial,sans-serif\", "
                          "fontsize=10];")
           << std::endl;
        ss << fmt::format("edge [fontname=\"Helvetica,Arial,sans-serif\", "
                          "fontsize=8];")
           << std::endl;
        ss << "environment [label=\"" << m_name << "\", shape=Mdiamond];"
           << std::endl;

        for (auto& [name, graph] : m_graphs)
        {
            ss << std::endl;
            ss << "subgraph cluster_" << name << " {" << std::endl;
            ss << "label=\"" << name << "\";" << std::endl;
            ss << "style=filled;" << std::endl;
            ss << "color=lightgrey;" << std::endl;
            ss << fmt::format("node [style=filled,color=white];") << std::endl;
            for (auto& [name, asset] : graph.m_nodes)
            {
                ss << name << " [label=\"" << name << "\"];" << std::endl;
            }
            for (auto& [parent, children] : graph.m_edges)
            {
                if (graph.node(parent)->m_filters.size() > 0)
                {
                    ss << fmt::format("subgraph cluster_filters_{}{{", parent)
                       << std::endl;
                    ss << "label=\"\";" << std::endl;
                    ss << "color=\"blue\";" << std::endl;
                    ss << "style=default;" << std::endl;
                    for (auto& filter : graph.node(parent)->m_filters)
                    {
                        ss << filter << " [label=\"" << filter << "\"];"
                           << std::endl;
                    }
                    ss << "}" << std::endl;
                    for (auto& filter : graph.node(parent)->m_filters)
                    {
                        ss << fmt::format("{} -> {} [ltail={} "
                                          "lhead=cluster_filters_{}];",
                                          parent,
                                          filter,
                                          parent,
                                          parent)
                           << std::endl;
                    }
                    for (auto& child : children)
                    {
                        for (auto& filter : graph.node(parent)->m_filters)
                        {
                            ss << fmt::format(
                                      "{} -> {} [ltail=cluster_filters_{} "
                                      "lhead={}];",
                                      filter,
                                      child,
                                      parent,
                                      child)
                               << std::endl;
                        }
                    }
                }
                else
                {
                    for (auto& child : children)
                    {
                        ss << parent << " -> " << child << ";" << std::endl;
                    }
                }
            }
            ss << "}" << std::endl;
            ss << "environment -> " << name << "Input;" << std::endl;
        }
        ss << "}\n";
        return ss.str();
    }

    Expression getExpression() const
    {
        // Expression of the environment, expression to be returned.
        // All subgraphs are added to this expression.
        std::shared_ptr<Operation> environment = Chain::create(m_name, {});

        // Iterate over subgraphs creating the root subgraph expression
        for (auto& [name, graph] : m_graphs)
        {
            auto graphType = graph.node(graph.root())->m_type;

            // Create root subgraph expression
            std::shared_ptr<Operation> root;
            switch (graphType)
            {
                case Asset::Type::DECODER:
                    root = Or::create(graph.node(graph.root())->m_name, {});
                    break;
                case Asset::Type::RULE:
                case Asset::Type::OUTPUT:
                    root =
                        Broadcast::create(graph.node(graph.root())->m_name, {});
                    break;
                default: throw std::runtime_error("Unsupported asset type");
            }
            // Add subgraph to environment expression
            environment->getOperands().push_back(root);

            // Build rest of the graph
            std::map<std::string, Expression>
                sharedParents; // Avoid duplicating nodes when multiple
                               // parents
            auto visit = [&](const std::string& current,
                             auto& visitRef) -> Expression
            {
                // If node is already built, return it
                if (sharedParents.find(current) != sharedParents.end())
                {
                    return sharedParents[current];
                }
                else
                {
                    // Create node
                    auto asset = graph.node(current);
                    std::shared_ptr<Operation> assetChildren;

                    // Children expression depends on the type of the graph
                    switch (graphType)
                    {
                        case Asset::Type::DECODER:
                            assetChildren = Or::create("children", {});
                            break;
                        case Asset::Type::RULE:
                        case Asset::Type::OUTPUT:
                            assetChildren = Broadcast::create("children", {});
                            break;

                        default:
                            throw std::runtime_error(
                                "Unsupported asset graph type");
                    }


                    std::shared_ptr<Operation> assetNode;
                    // If node has filters, add them before the children
                    if (asset->m_filters.size() > 0)
                    {
                        auto filters = And::create("filters", {});
                        for (auto& filter : asset->m_filters)
                        {
                            filters->getOperands().push_back(
                                m_assets.at(filter)->getExpression());
                        }
                        filters->getOperands().push_back(assetChildren);
                        assetNode = Implication::create(
                            asset->m_name + "Node",
                            asset->getExpression(),
                            {filters});
                    }
                    else
                    {
                        assetNode = Implication::create(asset->m_name + "Node",
                                                        asset->getExpression(),
                                                        assetChildren);
                    }

                    // If has multiple parents, add to sharedParents
                    if (asset->m_parents.size() > 1)
                    {
                        sharedParents.insert(
                            std::make_pair(current, assetNode));
                    }

                    // Visit children and add them to the children node
                    for (auto& child : graph.m_edges.at(current))
                    {
                        assetChildren->getOperands().push_back(
                            visitRef(child, visitRef));
                    }

                    return assetNode;
                }
            };

            // Visit root childs and add them to the root expression
            for (auto& child : graph.m_edges.at(graph.root()))
            {
                root->getOperands().push_back(visit(child, visit));
            }
        }

        return environment;
    }

    // Expression getExpression() const
    // {
    //     auto expression = Chain::create("environment", {});
    //     std::unordered_map<std::string, Expression>
    //     decodersMultipleParent; auto visit = [this,
    //     &decodersMultipleParent](
    //                      std::string current, auto& refVisit) ->
    //                      Expression
    //     {
    //         if (decodersMultipleParent.find(current) !=
    //             decodersMultipleParent.end())
    //         {
    //             return decodersMultipleParent.at(current);
    //         }
    //         else
    //         {
    //             std::shared_ptr<Operation> children;
    //             std::shared_ptr<Operation> node;
    //             switch (m_decoderGraph.node(current)->m_type)
    //             {
    //                 case Asset::ExpressionType::Or:
    //                     children = Or::create("children", {});
    //                     node = Implication::create(
    //                         current + "Node",
    //                         m_decoderGraph.node(current)->m_expression,
    //                         children);
    //                     break;
    //                 case Asset::ExpressionType::And:
    //                     children = And::create("children", {});
    //                     node = Implication::create(
    //                         current + "Node",
    //                         m_decoderGraph.node(current)->m_expression,
    //                         children);
    //                     break;
    //                 default: break;
    //             }

    //             if (m_decoderGraph.m_edges.find(current) !=
    //                 m_decoderGraph.m_edges.end())
    //             {
    //                 for (const auto& child :
    //                 m_decoderGraph.m_edges.at(current))
    //                 {
    //                     children->getOperands().push_back(
    //                         refVisit(child, refVisit));
    //                 }
    //             }

    //             if (std::count_if(m_decoderGraph.m_edges.begin(),
    //                               m_decoderGraph.m_edges.end(),
    //                               [current](auto& pair)
    //                               {
    //                                   return pair.first != current &&
    //                                          std::find(pair.second.begin(),
    //                                                    pair.second.end(),
    //                                                    current) !=
    //                                              pair.second.end();
    //                               }) > 1)
    //             {
    //                 decodersMultipleParent.insert(
    //                     std::make_pair(current, node));
    //             }

    //             return node;
    //         }
    //     };
    //     auto decoders = Or::create(m_decoderGraph.root(), {});
    //     for (const auto& child :
    //          m_decoderGraph.m_edges.at(m_decoderGraph.root()))
    //     {
    //         decoders->getOperands().push_back(visit(child, visit));
    //     }
    //     expression->getOperands().push_back(decoders);
    //     return expression;
    // }
};

#endif // _ENVIRONMENT_H
