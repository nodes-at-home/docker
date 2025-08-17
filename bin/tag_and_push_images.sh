#!/bin/bash

# junand 05.08.2025

set -e

# check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "jq is required but not installed. Please install jq to use this script."
    exit 1
fi

REGISTRY=nodesathome1:5000

# options
# -d dry run mode, do not tag and push images
# -r <registry> (default nodesathome1:5000)
# -i <image list> (default all images)
# -h show help
# -v verbose output
# -q quiet output

# parse options
while getopts "r:i:dhqv" opt; do
  case ${opt} in
    r )
      REGISTRY=$OPTARG
      ;;
    i )
      IMAGES=$OPTARG
      ;;
    d )
      echo "Dry run mode enabled, no images will be tagged or pushed."
      DRY_RUN=true
      ;;
    h )
      echo "Usage: $0 [-r <registry>] [-i <image list>]"
      echo "  -r <registry>   Specify the registry to push images to (default: nodesathome1:5000)"
      echo "  -i <image list> Specify the list of images to tag and push (default: all images)"
      echo "  -d              Dry run mode, do not tag and push images"
      echo "  -h              Show this help message"
      echo "  -q              Quiet mode, suppress output"
      echo "  -v              Verbose mode, show detailed output"
      exit 0
      ;;
    q )
      exec > /dev/null 2>&1
      ;;
    v )
      set -x
      ;;
    \? )
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

echo "target registry: ${REGISTRY}"

# retrieve all images, no matter running or not
IMAGES=$(docker image list --format json | jq -r .Repository | grep -v my_ | grep -v nodesathome1:5000 | sort | uniq)
# use the first parameter as image list
[ -n "$1" ] && IMAGES="$1"
echo "images to treat:"
echo "${IMAGES}"

echo "--------------------------------------------------"

# check and eventually tag and push all images
 for image in ${IMAGES};
 do 

    LIST_HUB=$(docker image list --format json ${image} | jq --ascii-output '. | [{ ID, Repository, Tag }] | map ( select ( .Tag != "<none>" ) ) | .[] ')
    TAG_HUB=$(echo ${LIST_HUB} | jq -r '. | .Tag ')
    ID_HUB=$(echo ${LIST_HUB} | jq -r '. | .ID ')

    LIST_REG=$(docker image list --format json ${REGISTRY}/${image} | jq --ascii-output '. | [{ ID, Repository, Tag }] | map ( select ( .Tag != "<none>" ) ) | .[] ')
    TAG_REG=$(echo ${LIST_REG} | jq -r '. | .Tag ')
    ID_REG=$(echo ${LIST_REG} | jq -r '. | .ID ')

    # echo "-> " ${image}":"${TAG_HUB}
    # echo ${ID_HUB} ">"${ID_REG}"<"
    # echo ""

    # only tag and push, when image were already tagged with private registry
    # images which are never tagged with private registry will not be pushed and must be initially tagged an pushed manually
    if [ -n "${ID_REG}" ] && [ "${ID_HUB}" != "${ID_REG}" ] && [ "${TAG_HUB}" == "${TAG_REG}" ]; then

        if [ -n "${DRY_RUN}" ]; then
            echo "Dry run: would tag and push ${image}:${TAG_HUB} to ${REGISTRY}/${image}:${TAG_HUB}"
            continue
        fi

        echo "Tagging ${image}:${TAG_HUB} with ${REGISTRY}/${image}:${TAG_HUB}"
        docker tag ${image}:${TAG_HUB} ${REGISTRY}/${image}:${TAG_HUB}

        echo "Pushing ${image} to ${REGISTRY}/${image}:${TAG_HUB}"
        docker push ${REGISTRY}/${image}:${TAG_HUB}
        # echo "Pushed ${image} to ${REGISTRY}/${image}"

    else

        if [ -z "${ID_REG}" ]; then
            echo "Image ${image}:${TAG_HUB} not found in registry ${REGISTRY}"
        elif [ "${ID_HUB}" == "${ID_REG}" ]; then
            echo "Image ${image}:${TAG_HUB} already tagged and pushed to ${REGISTRY}/${image}:${TAG_HUB}"
        elif [ "${TAG_HUB}" != "${TAG_REG}" ]; then
            echo "Image ${image}:${TAG_HUB} has different TAG in ${REGISTRY}/${image}:${TAG_REG}"
        else
            echo "will never be seen"
        fi

    fi

    echo "--------------------------------------------------"

done