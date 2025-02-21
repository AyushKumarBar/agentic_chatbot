import React from "react";


const formatDate = (isoString) => {
    const date = new Date(isoString);
    const day = date.getDate();
    const month = date.toLocaleString("en-US", { month: "short" });
    const year = date.getFullYear();
    return `${day} ${month} ${year}`;
  };

const SearchResults = ({ results }) => {
  return (
    <div className="">
  {Object.keys(results)
    .filter((category) => results[category] && results[category].length > 0) // Ensure non-empty categories
    .map((category) => (
      <div key={category} className="mb-6">
        <p className="text-sm font-bold mb-2 capitalize">{category}</p>
        <div className="flex overflow-x-scroll w-[350px] sm:w-full p-2 gap-2">
          {results[category]
            .filter(Boolean)
            .map((item, index) => (
              <div
                key={index}
                className="max-w-[170px] w-full bg-white rounded-2xl p-2 flex-shrink-0 border border-gray-200 hover:shadow-xl transition"
              >
                {item?.image && (
                  <img
                    src={item?.image}
                    alt={item?.title}
                    className="w-full h-20 object-cover rounded-lg"
                  />
                )}
                {item?.thumbnails?.length > 0 && (
                  <img
                    src={item?.thumbnails[0]}
                    alt={item?.title}
                    className="w-full h-20 object-cover rounded-lg"
                  />
                )}
                <p className="text-sm font-semibold mt-2 line-clamp-2">
                  {item?.title}
                </p>
                {(item?.date || item?.publish_time) && (
                  <p className="text-gray-500 text-xs mt-2">
                    {formatDate(item?.date || item?.publish_time)}
                  </p>
                )}
                <p className="text-gray-600 text-xs line-clamp-3">
                  {item?.body}
                </p>
                <a
                  href={item?.href || item?.url || item?.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-500 text-sm mt-2 inline-block"
                >
                  {category === "videos" ? "View" : "Read more"}
                </a>
              </div>
            ))}
        </div>
      </div>
    ))}
</div>

  );
};

export default SearchResults;
