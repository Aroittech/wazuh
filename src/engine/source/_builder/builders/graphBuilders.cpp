#include "graphBuilder.hpp"

#include <algorithm>
#include <any>
#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "_builder/event.hpp"
#include "_builder/expression.hpp"
#include "_builder/json.hpp"
#include "_builder/registry.hpp"

namespace builder::internals::builders
{

Expression<Event> orGraphBuilder(std::any definition)
{
    auto assets =
        std::any_cast<std::vector<std::tuple<std::string, Json>>>(definition);

    std::unordered_map<std::string, Expression<Event>> assetsStages;
    std::unordered_map<std::string, Expression<Event>> assetsChecks;
    std::unordered_map<std::string, std::vector<std::string>> assetChildrens;

    // This should be done on a function
    for(auto [name, def] : assets)
    {
        auto objDef = def.getObject();

        // Get check expression
        auto checkPos = std::find_if(
            objDef.begin(),
            objDef.end(),
            [](auto& tuple) { return std::get<0>(tuple) == "check"; });
        if (checkPos == objDef.end())
        {
            throw std::runtime_error(fmt::format(
                "Invalid asset [{}] definition: expected to have [check] stage",
                name));
        }
        objDef.erase(checkPos);
        auto check = std::get<1>(*checkPos);
        assetsChecks[name] = Registry::getBuilder("stage.check")
            (check);

        // Get parents names
        auto parentsPos = std::find_if(
            objDef.begin(),
            objDef.end(),
            [](auto& tuple) { return std::get<0>(tuple) == "parents"; });
        std::vector<std::string> parents;
        if (parentsPos != objDef.end())
        {
            auto tmp = std::get<1>(*parentsPos).getArray();
            std::transform(tmp.begin(),
                           tmp.end(),
                           std::back_inserter(parents),
                           [](auto& parent) { return parent.getString(); });
            objDef.erase(parentsPos);
        }
        else
        {
            parents.push_back("Root");
        }

        // Get metadata
        auto metadataPos = std::find_if(
            objDef.begin(),
            objDef.end(),
            [](auto& tuple) { return std::get<0>(tuple) == "metadata"; });
        std::vector<std::tuple<std::string, Json>> metadata;
        if (metadataPos != objDef.end())
        {
            metadata = std::get<1>(*metadataPos).getObject();
            objDef.erase(metadataPos);
        }

        // Get rest of stages
        std::vector<Expression<Event>> stages;
        for (auto& [stageName, stageDef] : objDef)
        {
            stages.push_back(Registry::getBuilder("stage." + stageName)
                             (stageDef));
        }
        assetsStages[name] = Expression<Event>::compose(Formula::And, stages);
    }

    // Now we have all components needed to build the graph




    // Make graph
    auto visitor = [&](std::string current,
                       auto& visitorRef) -> std::shared_ptr<Connectable>
    {
        auto currentNode = assetsNodes[current];
        if (childrenRel.find(current) != childrenRel.end())
        {
            auto childrenNode = ConnectableGroup::create(
                "children", ConnectableGroup::FIRST_SUCCESS);

            for (auto& child : childrenRel[current])
            {
                childrenNode->m_connectables.push_back(
                    visitorRef(child, visitorRef));
            }

            currentNode->m_connectables.push_back(childrenNode);
        }
        return currentNode;
    };

    auto rootNode =
        ConnectableAsset::create(ConnectableGroup::FIRST_SUCCESS, rootName);
    for (auto& childName : childrenRel[rootName])
    {
        rootNode->m_connectables.push_back(visitor(childName, visitor));
    }

    return rootNode;
}
};

RegisterBuilder FallibleGraph {
    "fallibleGraph",
    [](const std::any& definition) -> std::shared_ptr<Connectable>
    {
        auto [rootName, assetsNodes, childrenRel] = std::any_cast<std::tuple<
            std::string,
            std::unordered_map<std::string, std::shared_ptr<ConnectableGroup>>,
            std::unordered_map<std::string, std::unordered_set<std::string>>>>(
            definition);

        // Make graph
        auto visitor = [&](std::string current,
                           auto& visitorRef) -> std::shared_ptr<Connectable>
        {
            auto currentNode = assetsNodes[current];
            if (childrenRel.find(current) != childrenRel.end())
            {
                auto childrenNode = ConnectableGroup::create(
                    "children", ConnectableGroup::FALLIBLE_CHAIN);

                for (auto& child : childrenRel[current])
                {
                    childrenNode->m_connectables.push_back(
                        visitorRef(child, visitorRef));
                }
                childrenNode->m_connectables.push_back(currentNode);
            }
            return currentNode;
        };

        auto rootNode = ConnectableAsset::create(
            ConnectableGroup::FALLIBLE_CHAIN, rootName);
        for (auto& childName : childrenRel[rootName])
        {
            rootNode->m_connectables.push_back(visitor(childName, visitor));
        }

        return rootNode;
    }};

} // namespace
