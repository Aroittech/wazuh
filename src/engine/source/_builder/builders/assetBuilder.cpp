#include <algorithm>
#include <any>
#include <vector>

#include "_builder/environment.hpp"
#include "_builder/registry.hpp"

namespace builder::internals::builders
{

Expression assetBuilder(std::any definition)
{
    auto [name, stagesObj] = std::any_cast<
        std::tuple<std::string, std::vector<std::tuple<std::string, Json>>>>(
        definition);

    auto checkPos =
        std::find_if(stagesObj.begin(),
                     stagesObj.end(),
                     [](auto& stage) { return std::get<0>(stage) == "check"; });
    if (checkPos == stagesObj.end())
    {
        throw std::runtime_error("Asset definition must have a check");
    }
    auto condition =
        Registry::getBuilder("stage.check")(std::get<1>(*checkPos));
    stagesObj.erase(checkPos);

    auto stages = std::vector<Expression>();
    std::transform(stagesObj.begin(),
                   stagesObj.end(),
                   std::back_inserter(stages),
                   [](auto& stage) {
                       return Registry::getBuilder("stage." + std::get<0>(stage))(
                           std::get<1>(stage));
                   });
    auto consequence = And::create("consequence", {stages});
    auto expression =
        Implication::create(name, condition, consequence);

    return expression;
}

} // namespace builder::internals::builders
